/**
 * Plan B browser capture — hooks fetch() and posts responses to local API Monitor.
 */
(function () {
  const INGEST_URL = "http://127.0.0.1:8080/api/ingest";
  const API_PATTERN =
    /api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com/i;

  function parseModel(body) {
    if (!body) return null;
    try {
      const data = typeof body === "string" ? JSON.parse(body) : body;
      return data && data.model ? data.model : null;
    } catch {
      return null;
    }
  }

  async function sendIngest(url, method, model, responseText) {
    try {
      await fetch(INGEST_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          method,
          model_requested: model,
          response_body: responseText,
          source: "browser-extension",
        }),
      });
    } catch (e) {
      console.debug("[api-monitor] ingest failed", e);
    }
  }

  const originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const resp = await originalFetch.apply(this, args);
    try {
      const req = args[0];
      const init = args[1] || {};
      const url = typeof req === "string" ? req : req.url;
      if (!API_PATTERN.test(url)) return resp;

      const clone = resp.clone();
      const text = await clone.text();
      const model =
        parseModel(init.body) ||
        (typeof req !== "string" && req.body ? parseModel(await req.clone().text()) : null);
      sendIngest(url, init.method || "POST", model, text);
    } catch (e) {
      console.debug("[api-monitor] capture error", e);
    }
    return resp;
  };
})();
