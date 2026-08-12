"use client";

// /auth — sign-in / sign-up / LDAP entry page (single page, mode toggle).

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useApp } from "@/lib/store";
import { errorMessage } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";

type Mode = "signin" | "signup" | "ldap";

const APP_NAME = "JyotiGPT";

export default function AuthPage() {
  const { user, config, loading, signIn, signUp } = useApp();
  const router = useRouter();

  const [loaded, setLoaded] = useState(false);
  const [mode, setMode] = useState<Mode>("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [ldapUsername, setLdapUsername] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Redirect if a session already exists (e.g. after refresh or trusted-header
  // auth). Run after config loads so LDAP mode is known.
  useEffect(() => {
    if (!loading) {
      setLoaded(true);
      if (config?.auth.enable_ldap) {
        setMode("ldap");
      }
      if (user) {
        router.replace("/");
      }
    }
  }, [loading, config, user, router]);

  const submitHandler = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (submitting) return;
      setSubmitting(true);
      try {
        if (mode === "ldap") {
          await signIn(ldapUsername, password, true);
        } else if (mode === "signin") {
          await signIn(email, password);
        } else {
          await signUp(name, email, password);
        }
        toast.success("You're now logged in.");
        router.replace("/");
      } catch (error) {
        toast.error(errorMessage(error));
      } finally {
        setSubmitting(false);
      }
    },
    [submitting, mode, signIn, signUp, ldapUsername, password, email, name, router],
  );

  return (
    <div className="w-full h-screen max-h-[100dvh] text-white relative">
      <div className="w-full h-full absolute top-0 left-0 bg-white dark:bg-black"></div>

      <div className="w-full absolute top-0 left-0 right-0 h-8" />

      {loaded && (
        <>
          <div className="fixed m-10 z-50">
            <div className="flex space-x-2">
              <div className="self-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  crossOrigin="anonymous"
                  src="/favicon.png"
                  className="w-6 rounded-full"
                  alt="logo"
                />
              </div>
            </div>
          </div>

          <div className="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-50 text-black dark:text-white">
            <div className="w-full sm:max-w-md px-10 min-h-screen flex flex-col text-center">
              <div className="my-auto pb-10 w-full dark:text-gray-100">
                <form
                  className="flex flex-col justify-center"
                  onSubmit={submitHandler}
                >
                  <div className="mb-1">
                    <div className="text-2xl font-medium">
                      {mode === "ldap"
                        ? `Sign in to ${APP_NAME} with LDAP`
                        : mode === "signin"
                          ? `Sign in to ${APP_NAME}`
                          : `Sign up to ${APP_NAME}`}
                    </div>
                  </div>

                  <div className="flex flex-col mt-4">
                      {mode === "signup" && (
                        <div className="mb-2">
                          <div className="text-sm font-medium text-left mb-1">
                            Name
                          </div>
                          <input
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            type="text"
                            className="my-0.5 w-full text-sm outline-none bg-transparent"
                            autoComplete="name"
                            placeholder="Enter Your Full Name"
                            required
                          />
                        </div>
                      )}

                      {mode === "ldap" ? (
                        <div className="mb-2">
                          <div className="text-sm font-medium text-left mb-1">
                            Username
                          </div>
                          <input
                            value={ldapUsername}
                            onChange={(e) => setLdapUsername(e.target.value)}
                            type="text"
                            className="my-0.5 w-full text-sm outline-none bg-transparent"
                            autoComplete="username"
                            name="username"
                            placeholder="Enter Your Username"
                            required
                          />
                        </div>
                      ) : (
                        <div className="mb-2">
                          <div className="text-sm font-medium text-left mb-1">
                            Email
                          </div>
                          <input
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            type="email"
                            className="my-0.5 w-full text-sm outline-none bg-transparent"
                            autoComplete="email"
                            name="email"
                            placeholder="Enter Your Email"
                            required
                          />
                        </div>
                      )}

                      <div>
                        <div className="text-sm font-medium text-left mb-1">
                          Password
                        </div>
                        <input
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          type="password"
                          className="my-0.5 w-full text-sm outline-none bg-transparent"
                          placeholder="Enter Your Password"
                          autoComplete="current-password"
                          name="current-password"
                          required
                        />
                      </div>
                  </div>

                  <div className="mt-5">
                    {mode === "ldap" ? (
                      <button
                        type="submit"
                        disabled={submitting}
                        className="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5 disabled:opacity-50"
                      >
                        Authenticate
                      </button>
                    ) : (
                      <>
                        <button
                          type="submit"
                          disabled={submitting}
                          className="bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition w-full rounded-full font-medium text-sm py-2.5 disabled:opacity-50"
                        >
                          {submitting ? (
                            <span className="flex justify-center">
                              <Spinner className="size-4" />
                            </span>
                          ) : mode === "signin" ? (
                            "Sign in"
                          ) : (
                            "Create Account"
                          )}
                        </button>

                        {config?.auth.enable_signup && (
                          <div className="mt-4 text-sm text-center">
                            {mode === "signin"
                              ? "Don't have an account?"
                              : "Already have an account?"}
                            <button
                              className="font-medium underline"
                              type="button"
                              onClick={() =>
                                setMode(mode === "signin" ? "signup" : "signin")
                              }
                            >
                              {mode === "signin" ? "Sign up" : "Sign in"}
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </form>

                {config?.auth.enable_ldap && (
                  <div className="mt-2">
                    <button
                      className="flex justify-center items-center text-xs w-full text-center underline"
                      type="button"
                      onClick={() =>
                        setMode(mode === "ldap" ? "signin" : "ldap")
                      }
                    >
                      <span>
                        {mode === "ldap"
                          ? "Continue with Email"
                          : "Continue with LDAP"}
                      </span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
