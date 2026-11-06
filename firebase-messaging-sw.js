/* SarkariJobAlert FCM background worker */
importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyCNc3P7587EOfMuwStAeB9dDy0ybk_1Jwc",
  authDomain: "arkarijobalert-32102.firebaseapp.com",
  projectId: "arkarijobalert-32102",
  storageBucket: "arkarijobalert-32102.firebasestorage.app",
  messagingSenderId: "559517715385",
  appId: "1:559517715385:web:96c8720e48ca0bcf988468"
});

const messaging = firebase.messaging();
const SITE_URL = "https://sarkari-jobalert.com/";
const LOGO_URL = "/SarkariJobAlert_logo.png";

messaging.onBackgroundMessage((payload) => {
  const d = payload && payload.data ? payload.data : {};
  const target = d.url || SITE_URL;

  return self.registration.showNotification(
    d.title || "SarkariJobAlert Update",
    {
      body: d.body || "सरकारी जॉब अलर्ट: नई अपडेट जारी हुई है। पूरी जानकारी देखने के लिए यहाँ दबाएँ।",
      icon: LOGO_URL,
      image: LOGO_URL,
      badge: "/favicon.png",
      tag: d.tag || ("sja-" + (d.jobId || Date.now())),
      renotify: false,
      data: {
        url: target,
        jobId: String(d.jobId || "")
      },
      lang: "hi"
    }
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const target =
    (event.notification.data && event.notification.data.url) || SITE_URL;

  event.waitUntil((async () => {
    const windows = await clients.matchAll({
      type: "window",
      includeUncontrolled: true
    });

    for (const client of windows) {
      if ("navigate" in client) {
        await client.navigate(target);
        return client.focus();
      }
    }

    return clients.openWindow(target);
  })());
});
