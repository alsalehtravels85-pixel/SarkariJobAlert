/* Visitor opt-in. Never contains Firebase service-account credentials. */
(() => {
  const btn = document.getElementById("enableJobNotifications");
  const status = document.getElementById("pushNotificationStatus");
  const popup = document.getElementById("pushPopupBackdrop");
  const closeBtn = document.getElementById("closePushPopup");
  const laterBtn = document.getElementById("laterPushPopup");
  if (!btn || !status || !popup) return;
  const say = s => status.textContent = s;
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
  popup.addEventListener("click", e => { if (e.target === popup) closePopup(); });
  btn.addEventListener("click", async () => {
    btn.disabled = true; say("Notifications setup ho raha hai...");
    try {
      const cfg = window.SJA_CONFIG || {}, fc = window.SJA_FIREBASE_CONFIG || {};
      if (!window.isSecureContext || !("serviceWorker" in navigator) || !("Notification" in window)) throw new Error("Push notification ke liye HTTPS aur supported browser zaroori hai.");
      if (!window.supabase || !cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY) throw new Error("Supabase config missing hai.");
      if (!window.firebase || !fc.projectId || !window.SJA_VAPID_PUBLIC_KEY) throw new Error("Firebase/VAPID public config missing hai.");
      const permission = await Notification.requestPermission();
      if (permission !== "granted") { say("Permission allow nahi hui. Browser settings mein Notifications allow karein."); return; }
      if (!firebase.apps.length) firebase.initializeApp(fc);
      const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js", {scope:"/"});
      const messaging = firebase.messaging();
      const token = await messaging.getToken({vapidKey:window.SJA_VAPID_PUBLIC_KEY, serviceWorkerRegistration:registration});
      if (!token) throw new Error("Device token nahi mila.");
      const db = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
      const now = new Date().toISOString();
      const {error} = await db.from("push_subscriptions").upsert({
        token,
        user_agent: navigator.userAgent,
        enabled: true,
        created_at: now,
        updated_at: now
      }, {onConflict: "token", ignoreDuplicates: true});
      if (error) throw new Error("Device register nahi hua: "+error.message);
      say("Notifications ON! Is device par Vacancy, Admit Card aur Result alerts milenge.");
      btn.textContent = "✓ Notifications Enabled";
      try { sessionStorage.setItem("sjaPushPopupDismissed", "1"); } catch (_) {}
      window.setTimeout(() => popup.classList.remove("is-open"), 1800);
    } catch(e) { console.error("SJA push:",e); say(e.message || "Setup nahi ho paya."); }
    finally { btn.disabled = false; }
  });
})();
