const { spawn } = require("node:child_process");
const { rmSync } = require("node:fs");
const { join } = require("node:path");

const args = process.argv.slice(2);
const fresh = args.includes("--fresh");
const poll = args.includes("--poll");
const blockedTurboFlags = new Set(["--turbo", "--turbopack"]);
const nextArgs = args.filter(
  (arg) => arg !== "--fresh" && arg !== "--poll" && !blockedTurboFlags.has(arg)
);

if (args.some((arg) => blockedTurboFlags.has(arg))) {
  console.warn(
    "Turbopack is disabled for this app because it has been corrupting dev manifests after edits. Using the stable webpack dev server instead."
  );
}

if (fresh) {
  rmSync(join(process.cwd(), ".next"), { recursive: true, force: true });
}

const env = {
  ...process.env
};

if (poll) {
  env.WATCHPACK_POLLING = env.WATCHPACK_POLLING ?? "true";
  env.CHOKIDAR_USEPOLLING = env.CHOKIDAR_USEPOLLING ?? "true";
}

const child = spawn(
  process.execPath,
  [require.resolve("next/dist/bin/next"), "dev", ...nextArgs],
  {
    env,
    stdio: "inherit"
  }
);

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});

child.on("error", (error) => {
  console.error(error);
  process.exit(1);
});
