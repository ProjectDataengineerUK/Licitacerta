import { getApps, initializeApp } from "firebase/app";
import {
  GoogleAuthProvider,
  getAuth,
  onIdTokenChanged,
  signInWithPopup,
  signOut,
} from "firebase/auth";

const bypass = process.env.NEXT_PUBLIC_AUTH_BYPASS === "1";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? "bypass",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ?? "bypass",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ?? "bypass",
};

export const firebaseApp = bypass
  ? null
  : getApps().length === 0
    ? initializeApp(firebaseConfig)
    : getApps()[0];

export const auth = bypass ? null : getAuth(firebaseApp!);
export const googleProvider = new GoogleAuthProvider();

export { onIdTokenChanged, signInWithPopup, signOut };

export async function signInWithGoogle() {
  return signInWithPopup(auth, googleProvider);
}

export async function signOutUser() {
  return signOut(auth);
}
