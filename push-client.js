/* Visitor opt-in. Never contains Firebase service-account credentials. */
(() => {
  const btn = document.getElementById("enableJobNotifications");
  const status = document.getElementById("pushNotificationStatus");
  if (!btn || !status) return;
  const say = s => status.textContent = s;
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      const cfg = window.SJA_CONFIG || {}, fc = window.SJA_FIREBASE_CONFIG || {};
      if (!window.isSecureContext || !("serviceWorker" in navigator) || !("Notification" in window))
        throw new Error("Push notification ke liye HTTPS aur supported browser zaroori hai.");
      if (!window.supabase || !cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY)
        throw new Error("Supabase config missing hai.");
      if (!window.firebase || !fc.projectId || !window.SJA_VAPID_PUBLIC_KEY)
        throw new Error("Firebase/VAPID public config missing hai.");
      const permission = await Notification.requestPermission();
      if (permission !== "granted") { say("Notification permission allow nahi hui."); return; }
      if (!firebase.apps.length) firebase.initializeApp(fc);
      const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js", {scope:"/"});
      const messaging = firebase.messaging();
      const token = await messaging.getToken({vapidKey:window.SJA_VAPID_PUBLIC_KEY, serviceWorkerRegistration:registration});
      if (!token) throw new Error("Device token nahi mila.");
      const db = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
      const {error} = await db.from("push_subscriptions").upsert(
        {token, user_agent:navigator.userAgent, enabled:true, updated_at:new Date().toISOString()},
        {onConflict:"token", ignoreDuplicates:true}
      );
      if (error) throw new Error("Device register nahi hua: "+error.message);
      say("Notifications ON! Vacancy, Admit Card aur Result alerts isi device par milenge.");
      btn.textContent = "✓ Notifications Enabled";
    } catch(e) { console.error("SJA push:",e); say(e.message || "Setup nahi ho paya."); }
    finally { btn.disabled = false; }
  });
})();
