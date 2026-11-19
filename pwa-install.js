(() => {
  "use strict";
  const button = document.getElementById("installAppBtn");
  if (!button) return;

  let installPrompt = null;
  const isStandalone = () =>
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;

  if (isStandalone()) {
    button.hidden = true;
    return;
  }

  // Keep the existing Firebase Messaging worker; do not register a second
  // root-scope worker that could interrupt push notifications.
  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/firebase-messaging-sw.js", {
        scope: "/",
        updateViaCache: "none"
      }).catch(error => console.warn("SJA app worker registration:", error));
    }, { once: true });
  }

  window.addEventListener("beforeinstallprompt", event => {
    event.preventDefault();
    installPrompt = event;
    button.hidden = false;
  });

  window.addEventListener("appinstalled", () => {
    installPrompt = null;
    button.hidden = true;
  });

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) &&
    !window.MSStream;

  if (isIOS) button.hidden = false;

  button.addEventListener("click", async () => {
    if (installPrompt) {
      installPrompt.prompt();
      await installPrompt.userChoice;
      installPrompt = null;
      button.hidden = true;
      return;
    }
    if (isIOS) {
      alert("Safari ke Share button par tap karein, phir 'Add to Home Screen' chunein.");
      return;
    }
    if (isStandalone()) button.hidden = true;
  });
})();
