/* SarkariJobAlert FCM background worker. Keep at website root. */
importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js");
firebase.initializeApp({
  apiKey: "AIzaSyCNc3P7587EOfMuwStAeB9dDy0ybk_1Jwc",
  authDomain: "arkarijobalert-32102.firebaseapp.com",
  projectId: "sarkarijobalert-32102",
  storageBucket: "arkarijobalert-32102.firebasestorage.app",
  messagingSenderId: "559517715385",
  appId: "1:559517715385:web:96c8720e48ca0bcf988468"
});
const messaging = firebase.messaging();
messaging.onBackgroundMessage((payload) => {
  const d = payload && payload.data ? payload.data : {};
  return self.registration.showNotification(d.title || "SarkariJobAlert Update", {
    body: d.body || "Nayi update publish hui hai. Details dekhein.",
    icon: "/favicon.png", badge: "/favicon.png",
    tag: d.tag || ("sja-" + (d.jobId || Date.now())),
    data: { url: d.url || "https://sarkari-jobalert.com/" },
    renotify: false
  });
});
self.addEventListener("notificationclick", event => {
  event.notification.close();
  const target = event.notification.data && event.notification.data.url || "https://sarkari-jobalert.com/";
  event.waitUntil((async () => {
    const wins = await clients.matchAll({type:"window", includeUncontrolled:true});
    for (const w of wins) { if ("navigate" in w) { await w.navigate(target); return w.focus(); } }
    return clients.openWindow(target);
  })());
});
