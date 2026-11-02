// The managed preview owns this process; both children terminate with it.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
if (existsSync('.env.local')) process.loadEnvFile('.env.local');
const children = [];
if (process.env.CLINICAL_START_API !== "0") {
  children.push(
    spawn(
      process.env.CLINICAL_PYTHON || "python",
      [
        "-m",
        "uvicorn",
        "server.clinical:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8060",
      ],
      { cwd: "..", env: process.env, stdio: "inherit" },
    ),
  );
}
children.push(
  spawn("node", ["node_modules/vite/bin/vite.js", ...process.argv.slice(2)], {
    env: process.env,
    stdio: "inherit",
  }),
);
const stop = () => {
  for (const p of children) p.kill("SIGTERM");
};
process.on("SIGTERM", () => {
  stop();
  process.exit();
});
process.on("SIGINT", () => {
  stop();
  process.exit();
});
for (const p of children)
  p.on("exit", (code) => {
    stop();
    process.exit(code || 0);
  });
