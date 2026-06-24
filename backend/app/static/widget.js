(function() {
  // 1. Identify the script element and extract the tenant slug
  const scriptEl = document.currentScript || document.getElementById('replyone-widget-script');
  const tenantSlug = scriptEl ? scriptEl.getAttribute('data-tenant') : null;

  if (!tenantSlug) {
    console.error('ReplyOne Widget Error: data-tenant attribute is missing from the script tag.');
    return;
  }

  // 2. Generate or retrieve a persistent customer session ID
  let sessionId = localStorage.getItem('replyone_customer_session_id');
  if (!sessionId) {
    sessionId = 'cust_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('replyone_customer_session_id', sessionId);
  }

  // 3. Inject CSS for widget launcher and container
  const styleEl = document.createElement('style');
  styleEl.innerHTML = `
    .replyone-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: linear-gradient(135deg, #1E6FE8, #6366F1);
      box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 999999;
      border: none;
      outline: none;
    }
    .replyone-launcher:hover {
      transform: scale(1.08) translateY(-2px);
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
    }
    .replyone-launcher:active {
      transform: scale(0.95);
    }
    .replyone-launcher svg {
      width: 24px;
      height: 24px;
      fill: none;
      stroke: #ffffff;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
      transition: transform 0.35s ease;
    }
    .replyone-launcher.open svg {
      transform: rotate(90deg);
    }
    .replyone-container {
      position: fixed;
      bottom: 96px;
      right: 24px;
      width: 380px;
      height: 580px;
      max-height: calc(100vh - 120px);
      max-width: calc(100vw - 48px);
      border-radius: 16px;
      box-shadow: 0 12px 32px rgba(13, 27, 42, 0.25);
      background: #ffffff;
      z-index: 999998;
      overflow: hidden;
      border: 1px solid rgba(45, 63, 86, 0.08);
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
      transform: translateY(24px) scale(0.95);
      opacity: 0;
      pointer-events: none;
    }
    .replyone-container.open {
      transform: translateY(0) scale(1);
      opacity: 1;
      pointer-events: auto;
    }
    .replyone-iframe {
      width: 100%;
      height: 100%;
      border: none;
      background: transparent;
    }
    @media (max-width: 480px) {
      .replyone-container {
        bottom: 0;
        right: 0;
        width: 100%;
        height: 100%;
        max-height: 100%;
        max-width: 100%;
        border-radius: 0;
      }
      .replyone-launcher {
        bottom: 16px;
        right: 16px;
      }
    }
  `;
  document.head.appendChild(styleEl);

  // 4. Create Iframe Container
  const container = document.createElement('div');
  container.className = 'replyone-container';
  
  const iframe = document.createElement('iframe');
  iframe.className = 'replyone-iframe';
  iframe.src = `http://localhost:8000/static/widget.html?tenant=${tenantSlug}&session=${sessionId}`;
  container.appendChild(iframe);
  document.body.appendChild(container);

  // 5. Create Launcher Button
  const launcher = document.createElement('button');
  launcher.className = 'replyone-launcher';
  
  // Custom SVG path for standard chat bubble / X icon toggle
  const chatIcon = `
    <svg id="replyone-icon-chat" viewBox="0 0 24 24">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
  `;
  
  const closeIcon = `
    <svg id="replyone-icon-close" style="display:none;" viewBox="0 0 24 24">
      <line x1="18" y1="6" x2="6" y2="18"></line>
      <line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>
  `;

  launcher.innerHTML = chatIcon + closeIcon;
  document.body.appendChild(launcher);

  // 6. Interactive Click Toggle
  let isOpen = false;
  launcher.addEventListener('click', () => {
    isOpen = !isOpen;
    if (isOpen) {
      container.classList.add('open');
      launcher.classList.add('open');
      document.getElementById('replyone-icon-chat').style.display = 'none';
      document.getElementById('replyone-icon-close').style.display = 'block';
    } else {
      container.classList.remove('open');
      launcher.classList.remove('open');
      document.getElementById('replyone-icon-chat').style.display = 'block';
      document.getElementById('replyone-icon-close').style.display = 'none';
    }
  });

  // Listen to iframe height messages if needed
  window.addEventListener('message', (event) => {
    if (event.data === 'replyone-close') {
      launcher.click();
    }
  });
})();
