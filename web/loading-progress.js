// Installed before Pygbag so Python, WASM, package and game downloads count.
(() => {
  const unlockAudio = () => {
    const context = window.SDL2?.audioContext || window.Module?.SDL2?.audioContext;
    if (context && context.state === 'suspended') context.resume().catch(console.warn);
  };
  document.addEventListener('touchstart', unlockAudio, {passive: true});
  document.addEventListener('pointerdown', unlockAudio, {passive: true});
  document.addEventListener('keydown', unlockAudio);
  const originalFetch = window.fetch.bind(window);
  const state = window.slippyLoading = { bytes: 0, progress: 0, stage: 'Downloading Python and Pygame' };
  const paint = () => {
    const bar = document.getElementById('game-load-progress');
    const label = document.getElementById('game-load-label');
    if (bar) { bar.max = 100; bar.value = state.progress; }
    if (label) label.textContent = `${state.stage} · ${(state.bytes / 1048576).toFixed(1)} MB downloaded`;
  };
  window.fetch = async function(input, init) {
    const response = await originalFetch(input, init);
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (!response.ok || !response.body || !/pygame-web|slippy-penguin\.(tar\.gz|apk)/.test(url || '')) return response;
    const archive = /slippy-penguin\.(tar\.gz|apk)/.test(url);
    const copy = response.clone();
    (async () => {
      const reader = copy.body.getReader();
      let received = 0;
      try {
        while (true) {
          const {done, value} = await reader.read();
          if (done) break;
          received += value.byteLength;
          state.bytes += value.byteLength;
          // Runtime sizes vary by browser/cache. This is an estimated overall
          // bar driven by bytes, never a timer or a claim of exact completion.
          const fraction = archive ? 70 + 25 * Math.min(1, received / 12210733) : 70 * state.bytes / (state.bytes + 12 * 1048576);
          state.progress = Math.max(state.progress, Math.min(95, fraction));
          state.stage = archive ? 'Downloading game assets' : 'Downloading Python and Pygame';
          paint();
        }
        if (archive) { state.progress = 95; state.stage = 'Starting Pygame'; paint(); }
      } catch (error) { console.warn('Loading progress unavailable', error); }
    })();
    // Preserve response URL, headers and streaming behavior for the runtime.
    return response;
  };
  setInterval(paint, 150);
})();
