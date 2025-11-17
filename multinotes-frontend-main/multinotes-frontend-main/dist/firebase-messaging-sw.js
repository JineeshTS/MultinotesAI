// importScripts("https://www.gstatic.com/firebasejs/^10.8.0/firebase-app.js");
// importScripts("https://www.gstatic.com/firebasejs/^10.8.0/firebase-messaging.js");

// importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js');
// importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js');
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js');
// Initialize the Firebase app in the service worker
// "Default" Firebase configuration (prevents errors)
const firebaseConfig = {
 
    apiKey: "AIzaSyBkPav0_aCU4I6pueaJzeQbVW6CrLk13bM",
 
    authDomain: "multinoteai.firebaseapp.com",
 
    projectId: "multinoteai",
 
    storageBucket: "multinoteai.appspot.com",
 
    messagingSenderId: "24655173706",
 
    appId: "1:24655173706:web:cec1b886d94a8906c62eb3",
 
    measurementId: "G-3K8ZLDM5SC"
 
};

firebase.initializeApp(firebaseConfig);

// Retrieve firebase messaging
const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log(payload, "Hello frpom firebase-messaging-sw.js")
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: payload.notification.image,
  };

self.registration.showNotification(notificationTitle, notificationOptions);
});