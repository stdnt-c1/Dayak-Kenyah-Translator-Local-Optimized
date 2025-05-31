const API_URL = 'http://localhost:8000';
let currentLang = 'id'; // 'id' for Indonesian, 'dyk' for Dayak Kenyah

// Generate unique request ID
function generateRequestId() {
    return 'req-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

// Format timestamp
function getTimestamp() {
    const now = new Date();
    const date = now.toLocaleDateString('en-GB').split('/').join('-');
    const time = now.toLocaleTimeString('en-GB');
    return `D:${date}#T:${time}`;
}

// Error handling to debug loading issues
window.onerror = function(message, source, lineno, colno, error) {
    console.error('JavaScript Error:', message, 'at', source, ':', lineno, ':', colno);
    if (document.getElementById('interactive-preloader') && 
        !document.getElementById('interactive-preloader').classList.contains('hidden')) {
        let errorDiv = document.createElement('div');
        errorDiv.style.position = 'fixed';
        errorDiv.style.bottom = '10px';
        errorDiv.style.left = '10px';
        errorDiv.style.right = '10px';
        errorDiv.style.backgroundColor = '#ffeeee';
        errorDiv.style.color = '#cc0000';
        errorDiv.style.padding = '10px';
        errorDiv.style.borderRadius = '5px';
        errorDiv.style.zIndex = '10000';
        errorDiv.style.fontSize = '12px';
        errorDiv.style.maxHeight = '150px';
        errorDiv.style.overflow = 'auto';
        errorDiv.innerHTML = '<strong>Debug Error:</strong> ' + message;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            document.getElementById('interactive-preloader').classList.add('hidden');
            document.body.classList.add('loaded');
        }, 8000);
    }
    return false;
};
    
    // Check browser capabilities
    const checkBrowser = () => {
        let result = {
            fetch: typeof fetch !== 'undefined',
            promises: typeof Promise !== 'undefined',
            localStorage: (function() {
                try {
                    localStorage.setItem('test', 'test');
                    localStorage.removeItem('test');
                    return true;
                } catch(e) {
                    return false;
                }
            })(),
            json: typeof JSON !== 'undefined'
        };
        
        console.log('Browser capability check:', result);
        return result;
    };
    
    // Run browser check
    const browserCapabilities = checkBrowser();
    
    let currentTranslateLang = 'id';
    let currentTheme = (browserCapabilities.localStorage && localStorage.getItem('theme')) || 'light';

    const htmlEl = document.documentElement;
    const themeIcon = document.getElementById('theme-icon');
    const preloader = document.getElementById('interactive-preloader');

    function applyTheme(theme) {
        htmlEl.setAttribute('data-theme', theme);
        themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
        localStorage.setItem('theme', theme);
    }

    document.getElementById('theme-toggle').onclick = () => {
        applyTheme(currentTheme === 'light' ? (currentTheme = 'dark') : (currentTheme = 'light'));
    };

    applyTheme(currentTheme);

    // Canvas particle preloader
    const canvas = document.getElementById('preloader-canvas');
    const ctx = canvas.getContext('2d');
    let particles = [], mouse = { x: null, y: null, radius: 80 };

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    class Particle {
        constructor(x, y) {
            this.x = x; this.y = y;
            this.size = Math.random() * 4 + 1;
            this.density = Math.random() * 20 + 5;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = (Math.random() - 0.5) * 0.5;
        }
        draw() {
            ctx.fillStyle = getComputedStyle(htmlEl).getPropertyValue('--canvas-particle-color');
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
        update() {
            if (mouse.x !== null && mouse.y !== null) {
                let dx = mouse.x - this.x;
                let dy = mouse.y - this.y;
                let dist = Math.hypot(dx, dy) || 0.1;
                let force = Math.max((mouse.radius - dist) / mouse.radius, 0);
                let dirX = (dx / dist) * force * this.density * 0.1;
                let dirY = (dy / dist) * force * this.density * 0.1;
                if (dist < mouse.radius) {
                    this.x -= dirX; this.y -= dirY;
                }
            }
            this.x += this.vx; this.y += this.vy;
            if (this.x < -this.size) this.x = canvas.width + this.size;
            if (this.x > canvas.width + this.size) this.x = -this.size;
            if (this.y < -this.size) this.y = canvas.height + this.size;
            if (this.y > canvas.height + this.size) this.y = -this.size;
        }
    }

    function initParticles() {
        particles = [];
        let count = Math.min(150, (canvas.width * canvas.height) / 10000);
        for (let i = 0; i < count; i++) {
            particles.push(new Particle(Math.random() * canvas.width, Math.random() * canvas.height));
        }
    }

    function connectParticles() {
        for (let a = 0; a < particles.length; a++) {
            for (let b = a + 1; b < particles.length; b++) {
                let dx = particles[a].x - particles[b].x;
                let dy = particles[a].y - particles[b].y;
                let dist = Math.hypot(dx, dy);
                if (dist < 70) {
                    let opacity = 1 - dist / 70;
                    ctx.strokeStyle = getComputedStyle(htmlEl).getPropertyValue('--canvas-line-color').replace(/[\d\.]+\)$/, (opacity * 0.5) + ')');
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(particles[a].x, particles[a].y);
                    ctx.lineTo(particles[b].x, particles[b].y);
                    ctx.stroke();
                }
            }
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => { p.update(); p.draw(); });
        connectParticles();
        requestAnimationFrame(animate);
    }

    window.addEventListener('resize', () => { resizeCanvas(); initParticles(); });
    window.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });
    canvas.addEventListener('touchmove', e => { e.preventDefault(); mouse.x = e.touches[0].clientX; mouse.y = e.touches[0].clientY; }, { passive: false });
    window.addEventListener('touchend', () => { mouse.x = mouse.y = null; });

    resizeCanvas();
    initParticles();
    animate();

    // Enhanced page loading logic with fallbacks
    let loadingTimedOut = false;
    
    // Fallback timer in case load event doesn't fire
    const loadingFallbackTimer = setTimeout(() => {
        loadingTimedOut = true;
        console.log('Loading fallback triggered');
        preloader.classList.add('hidden');
        document.body.classList.add('loaded');
    }, 5000);
    
    // Normal load event handler
    window.addEventListener('load', () => {
        if (!loadingTimedOut) {
            clearTimeout(loadingFallbackTimer);
            setTimeout(() => {
                preloader.classList.add('hidden');
                document.body.classList.add('loaded');
            }, 3000);
        }
    });
    
    // DOMContentLoaded as backup (will fire earlier than load)
    document.addEventListener('DOMContentLoaded', () => {
        if (!loadingTimedOut) {
            setTimeout(() => {
                preloader.classList.add('hidden');
                document.body.classList.add('loaded');
            }, 4000);
        }
    });

// Added error handling for API requests
async function fetchWithErrorHandling(url, options) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("API request failed:", error);
        throw error;
    }
}

// Updated translation function to use fetchWithErrorHandling
async function translateText() {
    const inputTextElement = document.getElementById("inputText");
    const translatorLoader = document.getElementById("translatorLoader");
    const outputTextElement = document.getElementById("outputText");

    const inputText = inputTextElement.value;

    if (!inputText.trim()) {
        outputTextElement.textContent = "Please enter some text to translate.";
        return;
    }

    translatorLoader.style.display = "block";
    outputTextElement.textContent = "Translating...";

    try {
        const data = await fetchWithErrorHandling("/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                client: "webInterface",
                requestId: generateRequestId(),
                timestamp: getTimestamp(),
                payload: {
                    sourceLang: currentLang,
                    targetLang: currentLang === "id" ? "dyk" : "id",
                    text: inputText,
                    options: {
                        preserveFormatting: true,
                        preservePunctuation: true,
                        caseSensitive: false
                    }
                }
            })
        });

        outputTextElement.textContent = data.payload.translatedText;
    } catch (error) {
        outputTextElement.textContent = "Error connecting to translation service.";
    } finally {
        translatorLoader.style.display = "none";
    }
}

// Language swap function
function swapLanguage() {
    const currentLangEl = document.getElementById('currentLang');
    const targetLangEl = document.getElementById('swapLangTarget');
    const inputEl = document.getElementById('inputText');
    const outputEl = document.getElementById('outputText');
    
    // Animate the swap button
    const swapButton = document.querySelector('.swap-button');
    swapButton.style.transform = 'rotate(180deg)';
    setTimeout(() => swapButton.style.transform = '', 300);
    
    // Swap the languages
    const tempLang = currentLangEl.textContent;
    currentLangEl.textContent = targetLangEl.textContent;
    targetLangEl.textContent = tempLang;
    
    // Swap the text content
    const tempText = inputEl.value;
    inputEl.value = outputEl.textContent === 'Hasil terjemahan akan muncul di sini.' ? '' : outputEl.textContent;
    outputEl.textContent = tempText || 'Hasil terjemahan akan muncul di sini.';
    
    // Update the internal language state
    currentLang = currentLang === 'id' ? 'dyk' : 'id';
    
    // Focus the input
    inputEl.focus();
}

// Auto-resize textarea
document.getElementById('inputText').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Input event handler with debouncing
let translateTimeout;
document.getElementById('inputText').addEventListener('input', (e) => {
    const inputText = e.target.value.trim();
    const translatorLoader = document.getElementById('translatorLoader');
    const outputTextElement = document.getElementById('outputText');

    clearTimeout(translateTimeout);

    if (!inputText) {
        outputTextElement.textContent = 'Hasil terjemahan akan muncul di sini.';
        return;
    }

    translatorLoader.style.display = 'block';
    
    // Auto-translate after 500ms of no typing
    translateTimeout = setTimeout(() => {
        translateText();
    }, 500);
});

// Make translateText globally available
window.translateText = translateText;

// Initialize translation-related elements
document.addEventListener('DOMContentLoaded', () => {
    // Reset translation state
    const outputTextElement = document.getElementById('outputText');
    if (outputTextElement) {
        outputTextElement.textContent = 'Hasil terjemahan akan muncul di sini.';
    }
    
    // Make sure swap language is globally available
    window.swapLanguage = swapLanguage;
    
    // Add keyboard shortcut for translation (Ctrl+Enter or Cmd+Enter)
    document.getElementById('inputText').addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            translateText();
        }
    });
});

function selectTranslatedText() {
    const outputText = document.getElementById('outputText');
    if (document.body.createTextRange) {
        const range = document.body.createTextRange();
        range.moveToElementText(outputText);
        range.select();
    } else if (window.getSelection) {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(outputText);
        selection.removeAllRanges();
        selection.addRange(range);
    }
    
    // Try to copy to clipboard
    try {
        document.execCommand('copy');
        // Show brief feedback
        const btn = document.querySelector('.select-text-btn');
        const originalText = btn.innerHTML;
        btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
        </svg> Tersalin!`;
        setTimeout(() => btn.innerHTML = originalText, 2000);
    } catch (err) {
        console.log('Copy not supported');
    }
}
