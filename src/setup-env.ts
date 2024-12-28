import log from "loglevel";
import prefix from "loglevel-plugin-prefix";
import dotenv from "dotenv";

dotenv.config();

export function setupLog() {
  prefix.reg(log);
  prefix.apply(log, {
    timestampFormatter: function (date) {
      return date.toLocaleString();
    },
  });
  if (!(process.env.LOG_LEVEL == "info" || process.env.LOG_LEVEL == "debug")) {
    throw new Error("LOG_LEVEL must be 'info' or 'debug'");
  }

  log.setLevel(process.env.LOG_LEVEL);
}

export function getLLMConfig() {
  if (
    !process.env.OPENAI_API_KEY ||
    !process.env.OPENAI_BASE_URL ||
    !process.env.MODEL
  ) {
    log.warn(
      "OPENAI_API_KEY, OPENAI_BASE_URL, and MODEL must be set in .env file"
    );
    process.exit(1);
  }
  log.info("Using model: " + process.env.MODEL);
  return {
    apiKey: process.env.OPENAI_API_KEY,
    baseURL: process.env.OPENAI_BASE_URL,
    model: process.env.MODEL,
    max_tokens: Number(process.env.MAX_TOKENS),
  };
}

export function getRemoteEndpoint() {
  if (!process.env.DIFF_ENDPOINT) {
    log.warn("DIFF_ENDPOINT must be set in .env file");
    process.exit(1);
  }
  if (!process.env.ASSET_ENDPOINT) {
    log.warn("ASSET_ENDPOINT must be set in .env file");
    process.exit(1);
  }
  return {
    diffEndpoint: process.env.DIFF_ENDPOINT,
    assetEndpoint: process.env.ASSET_ENDPOINT,
  };
}
