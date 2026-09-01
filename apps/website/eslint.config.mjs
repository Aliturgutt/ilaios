import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,
  {
    rules: {
      "react/no-unescaped-entities": [
        "error",
        {
          forbid: [
            { char: ">", alternatives: ["&gt;"] },
            { char: "}", alternatives: ["&#125;"] },
            { char: "\"", alternatives: ["&quot;", "&ldquo;", "&#34;", "&rdquo;"] },
          ],
        },
      ],
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
