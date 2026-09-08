import { useState } from "react";
import { ArrowRight, ShieldCheck, Waves } from "lucide-react";
import Logo from "../components/Logo";

export default function Login({ onLogin }) {
  const [isSignup, setIsSignup] = useState(true);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();

    if (isSignup) {
      if (password !== confirmPassword) {
        alert("Passwords do not match.");
        return;
      }

      alert("Account created successfully. You can now sign in.");
      setIsSignup(false);
      setPassword("");
      setConfirmPassword("");
      return;
    }

    onLogin();
  };

  return (
    <div className="login-page">
      {/* Left visual section */}
      <div className="login-visual">
        <div className="login-glow" />

        <div className="login-brand">
          <Logo />
        </div>

        <div className="login-copy">
          <span className="eyebrow">MARINE INTELLIGENCE PLATFORM</span>

          <h1>SONARIES</h1>

          <p>
            Smart sonar analysis for detecting and reviewing underwater
            anomalies.
          </p>
        </div>

        <div className="login-footer">
          <Waves size={18} />
          Side-scan sonar analysis
        </div>
      </div>

      {/* Right form section */}
      <div className="login-panel">
        <div className="login-form-wrap">
          <div className="mobile-logo">
            <Logo />
          </div>

          <span className="eyebrow">
            {isSignup ? "GET STARTED" : "WELCOME BACK"}
          </span>

          <h2>
            {isSignup
              ? "Create your SONARIES account"
              : "Sign in to SONARIES"}
          </h2>

          <p className="muted">
            {isSignup
              ? "Join SONARIES to begin your marine survey analysis."
              : "Sign in to continue to your marine intelligence workspace."}
          </p>

          <form onSubmit={handleSubmit}>
            {isSignup && (
              <label>
                Full name
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter your full name"
                  required
                />
              </label>
            )}

            <label>
              Email address
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email address"
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />
            </label>

            {isSignup && (
              <label>
                Confirm password
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                  required
                />
              </label>
            )}

            {!isSignup && (
              <div className="form-row">
                <label className="check">
                  <input type="checkbox" defaultChecked />
                  Remember me
                </label>

                <a href="#forgot">Forgot password?</a>
              </div>
            )}

            <button className="primary-btn full" type="submit">
              {isSignup ? "Create account" : "Sign in"}
              <ArrowRight size={18} />
            </button>
          </form>

          <div className="secure-note">
            <ShieldCheck size={17} />
            {isSignup
              ? "Create your account to access SONARIES."
              : "Demo mode: any valid email and password will work."}
          </div>

          <div className="auth-switch">
            {isSignup
              ? "Already have an account?"
              : "Don't have an account?"}

            <button
              type="button"
              onClick={() => setIsSignup(!isSignup)}
            >
              {isSignup ? "Sign in" : "Sign up"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
