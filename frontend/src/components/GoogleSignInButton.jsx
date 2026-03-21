import { useEffect, useEffectEvent, useRef, useState } from "react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

let googleScriptPromise = null;

function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (googleScriptPromise) return googleScriptPromise;

  googleScriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-google-identity="true"]');
    if (existing) {
      existing.addEventListener("load", resolve, { once: true });
      existing.addEventListener("error", reject, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.dataset.googleIdentity = "true";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google sign-in"));
    document.head.appendChild(script);
  });

  return googleScriptPromise;
}

export default function GoogleSignInButton({ onCredential, onError, disabled = false }) {
  const buttonRef = useRef(null);
  const [ready, setReady] = useState(false);

  const handleCredential = useEffectEvent((response) => {
    if (!response?.credential) {
      onError?.("Google sign-in did not return a credential.");
      return;
    }
    onCredential?.(response.credential);
  });

  const handleError = useEffectEvent((message) => {
    onError?.(message);
  });

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || disabled) return undefined;

    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        if (cancelled || !buttonRef.current || !window.google?.accounts?.id) return;

        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleCredential,
        });

        buttonRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          shape: "pill",
          text: "continue_with",
          width: 320,
        });
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) handleError("Google sign-in is unavailable right now.");
      });

    return () => {
      cancelled = true;
    };
  }, [disabled]);

  if (!GOOGLE_CLIENT_ID) return null;

  return (
    <div className={disabled ? "pointer-events-none opacity-60" : ""}>
      <div ref={buttonRef} />
      {!ready ? <p className="mt-2 text-xs text-gray-500">Loading Google sign-in...</p> : null}
    </div>
  );
}
