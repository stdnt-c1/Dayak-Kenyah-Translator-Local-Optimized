// References to original code: This code is based on the RyuHiiragi project [https://github.com/RyuHiiragi/Dayak-Kenyah-Translator-ESP-32.git]

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <vector>
#include <DNSServer.h>
#include <ESPmDNS.h>

// AP Configuration
const char* AP_SSID = "DayakTranslator";  // Nama jaringan WiFi yang akan muncul
const char* AP_PASSWORD = "12345678";      // Password untuk koneksi WiFi
const byte DNS_PORT = 53;                  // Port DNS standar
const char* DNS_DOMAIN = "dayak.local";    // Domain lokal untuk akses web
IPAddress AP_IP(192, 168, 4, 1);          // IP address untuk akses web (192.168.4.1)
IPAddress AP_SUBNET(255, 255, 255, 0);     // Subnet mask

// Initialize servers
WebServer server(80);
DNSServer dnsServer;
StaticJsonDocument<16384> dict;

// Connection tracking
struct ClientInfo {
    IPAddress ip;
    unsigned long lastActivity;
};
std::vector<ClientInfo> activeClients;
const unsigned long CLIENT_TIMEOUT = 300000; // 5 minutes in milliseconds

// Refer to [https://github.com/RyuHiiragi/Dayak-Kenyah-Translator-ESP-32.git] for the full original dictionary JSON and HTML/CSS/JS.
// KAMUS DAYAK KENYAH
const char dictionary_json[] PROGMEM = R"rawliteral( ## DICTIONARY RAW STRING ## )rawliteral"; // Opted out for brevity

// 3. KODE HTML/CSS/JS
const char index_html[] PROGMEM = R"rawliteral( ## HTML, CSS, JS RAW STRING ## )rawliteral"; // Opted out for brevity

// Function declarations
void handleRoot();
void handleTranslate();
void handleMC();
void handleFill();
String extractQuotedText(const String& text);
void updateClientActivity(IPAddress clientIP);
void cleanupInactiveClients();

// BAGIAN ENGINE
bool refinedPartialMatch(const String& token, const String& dictWord) {
    String tokenLower = token;
    tokenLower.toLowerCase();
    String dictWordLower = dictWord;
    dictWordLower.toLowerCase();
    return tokenLower == dictWordLower;
}

std::vector<String> tokenizeSentence(const String& sentence) {
    String tmp = sentence;
    tmp.replace("?", " ");
    tmp.replace("!", " ");
    tmp.replace(".", " ");
    tmp.replace(",", " ");
    tmp.replace(":", " ");
    tmp.replace(";", " ");
    tmp.trim();

    std::vector<String> tokens;
    int start = 0;
    while (true) {
        int spacePos = tmp.indexOf(' ', start);
        if (spacePos == -1) {
            String last = tmp.substring(start);
            last.trim();
            if (last.length() > 0) tokens.push_back(last);
            break;
        } else {
            String piece = tmp.substring(start, spacePos);
            piece.trim();
            if (piece.length() > 0) tokens.push_back(piece);
            start = spacePos + 1;
        }
    }
    return tokens;
}

String translateSentencePartial(const String& input, const String& lang, const JsonObject& dictObj) {
    std::vector<String> tokens = tokenizeSentence(input);
    String result;
    
    // Set a maximum number of iterations to prevent potential hangs
    const int MAX_DICT_ITERATIONS = 1000;

    if (lang == "id") { // Indonesian -> Dayak
        for (auto &t : tokens) {
            String tLower = t;
            tLower.toLowerCase();
            bool found = false;
            int iterations = 0;
            
            for (JsonPair pair : dictObj) {
                String key = pair.key().c_str();
                String keyLower = key;
                keyLower.toLowerCase();
                
                if (tLower == keyLower) {
                    result += pair.value().as<String>() + " ";
                    found = true;
                    break;
                }
                
                iterations++;
                if (iterations >= MAX_DICT_ITERATIONS) {
                    break;
                }
            }
            
            if (!found) {
                result += t + " ";
            }
        }
    } else { // Dayak -> Indonesian
        for (auto &t : tokens) {
            String tLower = t;
            tLower.toLowerCase();
            bool found = false;
            int iterations = 0;
            
            for (JsonPair pair : dictObj) {
                String val = pair.value().as<String>();
                String valLower = val;
                valLower.toLowerCase();
                
                if (tLower == valLower) {
                    result += String(pair.key().c_str()) + " ";
                    found = true;
                    break;
                }
                
                iterations++;
                if (iterations >= MAX_DICT_ITERATIONS) {
                    break;
                }
            }
            
            if (!found) {
                result += t + " ";
            }
        }
    }
    
    result.trim();
    return result;
}

String doTranslation(const String& question, const String& questionLang, const String& outputLang, const JsonObject& dictObj) {
    if (questionLang == outputLang) {
        return question;
    }
    return translateSentencePartial(question, questionLang, dictObj);
}

// SETUP & ROUTING
void setup() {
    Serial.begin(115200);
    Serial.println("\nDayak Kenyah Translator Starting...");
    
    // Configure AP mode with optimized settings
    WiFi.disconnect();  // Disconnect any existing connection
    delay(100);
    
    WiFi.mode(WIFI_AP);
    WiFi.setAutoReconnect(true);
    
    // Set static IP configuration
    if (!WiFi.softAPConfig(AP_IP, AP_IP, AP_SUBNET)) {
        Serial.println("AP Configuration Failed!");
    }
    
    // Start the access point with the specified settings
    if (!WiFi.softAP(AP_SSID, AP_PASSWORD)) {
        Serial.println("AP Setup Failed!");
    } else {
        Serial.println("AP Mode Configured Successfully");
        Serial.print("Access Point Name: ");
        Serial.println(AP_SSID);
        Serial.print("AP IP address: ");
        Serial.println(WiFi.softAPIP());
    }
    
    // Setup DNS for captive portal (wildcard mapping)
    dnsServer.setErrorReplyCode(DNSReplyCode::NoError);
    if (!dnsServer.start(DNS_PORT, "*", AP_IP)) {
        Serial.println("DNS Server Failed to Start!");
    } else {
        Serial.println("DNS Server Started");
    }

    // Start mDNS responder for dayak.local (for devices that support mDNS)
    if (!MDNS.begin("dayak")) {
        Serial.println("Error setting up mDNS responder!");
    } else {
        MDNS.addService("http", "tcp", 80);
        Serial.println("mDNS responder started: http://dayak.local");
    }

    // Parse the dictionary JSON
    Serial.println("Loading dictionary...");
    DeserializationError error = deserializeJson(dict, dictionary_json);
    if (error) {
        Serial.println("Error parsing JSON: " + String(error.c_str()));
        return;
    }
    Serial.println("Dictionary loaded successfully");

    // Setup server routes
    server.on("/", HTTP_GET, handleRoot);
    server.on("/translate", HTTP_GET, handleTranslate);
    server.on("/mc", HTTP_GET, handleMC);
    server.on("/fill", HTTP_GET, handleFill);
    
    // Add a status endpoint to check server health
    server.on("/status", HTTP_GET, []() {
        String status = "Server is running. Uptime: " + String(millis() / 1000) + "s";
        server.send(200, "text/plain", status);
    });
    
    // Detect captive portal requests
    server.on("/generate_204", HTTP_GET, []() { // Android/Chrome OS captive portal check
        server.sendHeader("Location", "http://" + WiFi.softAPIP().toString());
        server.send(302, "text/plain", "");
    });
    server.on("/mobile/status.php", HTTP_GET, []() { // Android fallback captive portal check
        server.send(200, "text/html", "");
    });
    server.on("/hotspot-detect.html", HTTP_GET, []() { // iOS captive portal check
        server.send_P(200, "text/html", index_html);
    });
    server.on("/library/test/success.html", HTTP_GET, []() { // iOS captive portal check
        server.send_P(200, "text/html", index_html);
    });
    server.on("/success.txt", HTTP_GET, []() { // iOS captive portal check
        server.send(200, "text/plain", "success");
    });
    server.on("/ncsi.txt", HTTP_GET, []() { // Windows captive portal check
        server.send(200, "text/plain", "Microsoft NCSI");
    });
    
    // Handler default untuk semua path yang tidak dikenali
    server.onNotFound([]() {
        server.send_P(200, "text/html", index_html);
    });
    
    // Start the web server
    server.begin();
    Serial.println("HTTP Server Started");
    Serial.println("Dayak Kenyah Translator Ready!");
}

void loop() {
    // Process DNS requests to ensure captive portal works correctly
    dnsServer.processNextRequest();
    
    // Handle client requests with a small delay to prevent CPU hogging
    server.handleClient();
    
    // Periodically clean up inactive clients (every 30 seconds)
    static unsigned long lastCleanupTime = 0;
    unsigned long currentMillis = millis();
    if (currentMillis - lastCleanupTime > 30000) { // 30 seconds
        cleanupInactiveClients();
        lastCleanupTime = currentMillis;
    }
    
    // Small delay to prevent watchdog timer issues
    delay(1);
}

// HANDLER UTAMA (Root)
void handleRoot() {
    updateClientActivity(server.client().remoteIP());
    server.send_P(200, "text/html", index_html);
}

// HANDLER TERJEMAHAN
void handleTranslate() {
    updateClientActivity(server.client().remoteIP());
    if (!server.hasArg("text") || !server.hasArg("lang")) {
        server.send(400, "text/plain", "Parameter tidak lengkap");
        return;
    }
    String text = server.arg("text");
    String lang = server.arg("lang");
    String translated = translateSentencePartial(text, lang, dict.as<JsonObject>());
    server.send(200, "text/plain", translated);
}

// HANDLER MULTIPLE CHOICE (MC)
void handleMC() {
    updateClientActivity(server.client().remoteIP());
    if (!server.hasArg("question") || !server.hasArg("options") || !server.hasArg("lang")) {
        server.send(400, "text/plain", "Parameter tidak lengkap untuk soal pilihan ganda");
        return;
    }
    String question = server.arg("question");
    String optionsStr = server.arg("options");
    String lang = server.arg("lang");

    String extractedText = extractQuotedText(question);
    if (extractedText.length() == 0) {
        server.send(200, "text/plain", "Tidak ditemukan teks dalam tanda kutip atau tanda kurung.");
        return;
    }

    String fromLang = (lang == "id_to_dyk") ? "id" : "dyk";
    String translated = translateSentencePartial(extractedText, fromLang, dict.as<JsonObject>());
    translated.trim();
    translated.toLowerCase();

    const int maxOptions = 10;
    String options[maxOptions];
    int count = 0;
    int pos = 0;
    while (pos >= 0 && count < maxOptions) {
        int commaPos = optionsStr.indexOf(',', pos);
        if (commaPos == -1) {
            options[count++] = optionsStr.substring(pos);
            break;
        } else {
            options[count++] = optionsStr.substring(pos, commaPos);
            pos = commaPos + 1;
        }
    }
    for (int i = 0; i < count; i++) {
        options[i].trim();
        options[i].toLowerCase();
    }

    char answerLetter = '\0';
    const char letters[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    for (int i = 0; i < count; i++) {
        if (options[i] == translated) {
            answerLetter = letters[i];
            break;
        }
    }

    if (answerLetter == '\0') {
        server.send(200, "text/plain", "Jawaban yang benar tidak ditemukan dalam pilihan yang diberikan.");
    } else {
        String response = "Jawaban yang benar kemungkinan: ";
        response += answerLetter;
        response += ") ";
        response += options[answerLetter - 'A'];
        server.send(200, "text/plain", response);
    }
}

// HANDLER FILL-IN ANSWER (Soal Isian)
void handleFill() {
    updateClientActivity(server.client().remoteIP());
    if (!server.hasArg("question") || !server.hasArg("questionLang") || !server.hasArg("outputLang")) {
        server.send(400, "text/plain", "Parameter tidak lengkap untuk soal isian");
        return;
    }
    String question = server.arg("question");
    String qLang = server.arg("questionLang");
    String oLang = server.arg("outputLang");

    if ((qLang != "id" && qLang != "dyk") || (oLang != "id" && oLang != "dyk")) {
        server.send(400, "text/plain", "Parameter questionLang atau outputLang tidak valid. Gunakan 'id' atau 'dyk'.");
        return;
    }

    String extractedText = extractQuotedText(question);
    if (extractedText.length() == 0) {
        server.send(200, "text/plain", "Tidak ditemukan teks dalam tanda kutip atau tanda kurung.");
        return;
    }

    String answer = doTranslation(extractedText, qLang, oLang, dict.as<JsonObject>());
    answer.trim();

    if (answer.length() == 0) {
        server.send(200, "text/plain", "Tidak ditemukan kosakata yang sesuai. Periksa kembali soal Anda.");
        return;
    }
    
    String response = "Jawaban isian: " + answer;
    server.send(200, "text/plain", response);
}

// Fungsi extractQuotedText
String extractQuotedText(const String& text) {
    int startQuote = text.indexOf('"');
    int endQuote = -1;
    if (startQuote != -1) {
        endQuote = text.indexOf('"', startQuote + 1);
        if (endQuote != -1) {
            return text.substring(startQuote + 1, endQuote);
        }
    }
    
    int startParen = text.indexOf('(');
    int endParen = -1;
    if (startParen != -1) {
        endParen = text.indexOf(')', startParen + 1);
        if (endParen != -1) {
            return text.substring(startParen + 1, endParen);
        }
    }
    
    return "";
}

void updateClientActivity(IPAddress clientIP) {
    bool found = false;
    for (auto& client : activeClients) {
        if (client.ip == clientIP) {
            client.lastActivity = millis();
            found = true;
            break;
        }
    }
    if (!found && activeClients.size() < 50) { // Limit to 50 concurrent clients
        ClientInfo newClient = {clientIP, millis()};
        activeClients.push_back(newClient);
    }
}

void cleanupInactiveClients() {
    unsigned long currentTime = millis();
    for (auto it = activeClients.begin(); it != activeClients.end();) {
        if (currentTime - it->lastActivity > CLIENT_TIMEOUT) {
            it = activeClients.erase(it);
        } else {
            ++it;
        }
    }
}