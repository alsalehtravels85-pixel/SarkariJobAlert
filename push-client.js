/* SarkariJobAlert visitor push opt-in.
   Wait for the root Firebase service worker to become ACTIVE before asking
   Firebase Messaging to create a PushSubscription. */
(() => {
  "use strict";

  const btn = document.getElementById("enableJobNotifications");
  const status = document.getElementById("pushNotificationStatus");
  const popup = document.getElementById("pushPopupBackdrop");
  const closeBtn = document.getElementById("closePushPopup");
  const laterBtn = document.getElementById("laterPushPopup");
  if (!btn || !status || !popup) return;

  const say = message => { status.textContent = message; };
  const closePopup = () => {
    popup.classList.remove("is-open");
    try { sessionStorage.setItem("sjaPushPopupDismissed", "1"); } catch (_) {}
  };
  const openPopup = () => popup.classList.add("is-open");

  if ("Notification" in window && Notification.permission !== "granted") {
    let dismissed = false;
    try { dismissed = sessionStorage.getItem("sjaPushPopupDismissed") === "1"; } catch (_) {}
    if (!dismissed) window.setTimeout(openPopup, 2500);
  }

  closeBtn?.addEventListener("click", closePopup);
  laterBtn?.addEventListener("click", closePopup);
  popup.addEventListener("click", event => {
    if (event.target === popup) closePopup();
  });

  function waitUntilActive(registration) {
    if (registration.active) return Promise.resolve(registration);
    return new Promise((resolve, reject) => {
      const worker = registration.installing || registration.waiting;
      if (!worker) {
        reject(new Error("Service Worker install nahi hua. Website root par firebase-messaging-sw.js file check karein."));
        return;
      }
      const timeout = window.setTimeout(() => {
        worker.removeEventListener("statechange", onState);
        reject(new Error("Service Worker activate hone mein timeout. Page reload karke dobara try karein."));
      }, 20000);
      function onState() {
        if (registration.active || worker.state === "activated") {
          window.clearTimeout(timeout);
          worker.removeEventListener("statechange", onState);
          if (registration.active) resolve(registration);
          else reject(new Error("Service Worker active registration nahi mila. Page reload karke dobara try karein."));
        } else if (worker.state === "redundant") {
          window.clearTimeout(timeout);
          worker.removeEventListener("statechange", onState);
          reject(new Error("Service Worker install fail hua. firebase-messaging-sw.js file aur browser console check karein."));
        }
      }
      worker.addEventListener("statechange", onState);
      onState();
    });
  }

  btn.addEventListener("click", async () => {
    btn.disabled = true;
    say("Notifications setup ho raha hai...");

    try {
      const cfg = window.SJA_CONFIG || {};
      const fc = window.SJA_FIREBASE_CONFIG || {};

      if (!window.isSecureContext || !("serviceWorker" in navigator) || !("Notification" in window)) {
        throw new Error("Push notification ke liye HTTPS aur supported browser zaroori hai.");
      }
      if (!window.supabase || !cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY) {
        throw new Error("Supabase config missing hai.");
      }
      if (!window.firebase || !fc.projectId || !window.SJA_VAPID_PUBLIC_KEY) {
        throw new Error("Firebase/VAPID public config missing hai.");
      }

      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        say("Permission allow nahi hui. Browser settings mein Notifications allow karein.");
        return;
      }

      if (!firebase.apps.length) firebase.initializeApp(fc);

      // Register from the domain root so the worker controls the whole site.
      const swUrl = new URL("/firebase-messaging-sw.js", window.location.origin);
      const registration = await navigator.serviceWorker.register(swUrl.href, {
        scope: "/",
        updateViaCache: "none"
      });

      // register() can resolve while the worker is still installing.
      // Firebase getToken/PushManager requires an ACTIVE service worker.
      await waitUntilActive(registration);
      const readyRegistration = await navigator.serviceWorker.ready;
      const activeRegistration =
        registration.active ? registration :
        (readyRegistration && readyRegistration.active ? readyRegistration : null);

      if (!activeRegistration || !activeRegistration.active) {
        throw new Error("Active Service Worker nahi mila. Check karein: https://YOUR-DOMAIN/firebase-messaging-sw.js website root par open hona chahiye.");
      }

      const messaging = firebase.messaging();
      const token = await messaging.getToken({
        vapidKey: window.SJA_VAPID_PUBLIC_KEY,
        serviceWorkerRegistration: activeRegistration
      });

      if (!token) throw new Error("Device token nahi mila. Browser notification permission aur Firebase VAPID key check karein.");

      const db = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
      const now = new Date().toISOString();

      // INSERT is intentional: public visitors have INSERT permission only.
      const { error } = await db.from("push_subscriptions").insert({
        token,
        user_agent: navigator.userAgent,
        enabled: true,
        created_at: now,
        updated_at: now
      });

      if (error) {
        if (error.code === "23505") {
          say("Ye device pehle se subscribed hai.");
          btn.textContent = "✓ Already Subscribed";
          return;
        }
        throw new Error("Device register nahi hua: " + error.message);
      }

      say("Notifications ON! Is device par Vacancy, Admit Card aur Result alerts milenge.");
      btn.textContent = "✓ Notifications Enabled";
      try { sessionStorage.setItem("sjaPushPopupDismissed", "1"); } catch (_) {}
      window.setTimeout(() => popup.classList.remove("is-open"), 1800);
    } catch (error) {
      console.error("SJA push setup error:", error);
      say(error && error.message ? error.message : "Notification setup nahi ho paya.");
    } finally {
      btn.disabled = false;
    }
  });
})();
