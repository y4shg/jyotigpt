import nextConfig from "eslint-config-next";

const config = [
  ...nextConfig,
  {
    rules: {
      // These rules are overly strict for the patterns used in this codebase.
      // "set-state-in-effect" flags calling async functions in useEffect that
      // set state — a standard data-fetching pattern.
      "react-hooks/set-state-in-effect": "off",
      // "immutability" flags ref.current mutations inside callbacks, which is
      // the intended use case for mutable refs.
      "react-hooks/immutability": "off",
    },
  },
];

export default config;
