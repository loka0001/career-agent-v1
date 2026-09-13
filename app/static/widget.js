/* Commerce AI website widget — embeddable chat + event tracking.
 *
 * Usage:
 *   <script src="https://YOUR-HOST/widget.js" defer
 *     data-key="ck_XXXX" data-title="مساعد المتجر" data-color="#6366f1"
 *     data-position="left" data-dir="rtl" data-track="off"
 *     data-product-url-template="https://store.example/p/{id}"></script>
 *
 * No cookies are set. A random session key lives in sessionStorage only.
 * Tracking is disabled until the host calls setConsent(true).
 * CommerceAIOnAddToCart must return true, {success:true}, or a Promise of either.
 */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script) return;
  var API_KEY = script.getAttribute("data-key") || "";
  if (!API_KEY) { console.warn("[CommerceAI] data-key is required"); return; }
  var ORIGIN = new URL(script.src).origin;
  var TITLE = script.getAttribute("data-title") || "مساعد المتجر";
  var COLOR = script.getAttribute("data-color") || "#6366f1";
  var POSITION = script.getAttribute("data-position") === "left" ? "left" : "right";
  var DIR = script.getAttribute("data-dir") || "rtl";
  var TRACK = script.getAttribute("data-track") || "off";
  var URL_TEMPLATE = script.getAttribute("data-product-url-template") || "";
  var consented = false;

  var SKEY_NAME = "commerceai-session";
  var sessionKey = sessionStorage.getItem(SKEY_NAME);
  if (!sessionKey) {
    sessionKey = "s" + Array.from(crypto.getRandomValues(new Uint8Array(16)))
      .map(function (b) { return b.toString(16).padStart(2, "0"); }).join("");
    sessionStorage.setItem(SKEY_NAME, sessionKey);
  }

  function post(path, body) {
    var separator = path.indexOf("?") === -1 ? "?" : "&";
    return fetch(ORIGIN + path + separator + "key=" + encodeURIComponent(API_KEY), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Api-Key": API_KEY,
        "X-Client-Fingerprint": sessionKey,
      },
      body: JSON.stringify(body),
    }).then(function (response) {
      if (!response.ok) throw new Error("commerceai_http_" + response.status);
      return response.json();
    });
  }

  function track(eventType, data) {
    data = data || {};
    if (!consented) return Promise.resolve({ skipped: true });
    return post("/api/v1/public/events", {
      session_key: sessionKey,
      event_type: eventType,
      product_id: data.product_id || null,
      payload: data.payload || {},
      consented: true,
    }).catch(function () { /* tracking must never break the host page */ });
  }

  /* ---------- styles ---------- */
  var style = document.createElement("style");
  style.textContent =
    ".cai-btn{position:fixed;bottom:20px;" + POSITION + ":20px;z-index:2147483000;width:56px;height:56px;border-radius:50%;border:none;cursor:pointer;background:" + COLOR + ";color:#fff;font-size:24px;box-shadow:0 10px 30px rgba(0,0,0,.35);display:grid;place-items:center}" +
    ".cai-btn:hover{transform:translateY(-2px)}" +
    ".cai-panel{position:fixed;bottom:88px;" + POSITION + ":20px;z-index:2147483000;width:min(92vw,360px);height:min(70vh,520px);background:#0d1326;color:#eef2ff;border:1px solid rgba(165,180,235,.25);border-radius:16px;box-shadow:0 24px 60px rgba(0,0,0,.5);display:none;flex-direction:column;overflow:hidden;font:14px/1.6 system-ui,'Segoe UI',Tahoma,sans-serif}" +
    ".cai-panel.open{display:flex}" +
    ".cai-head{padding:12px 16px;background:" + COLOR + ";color:#fff;font-weight:700;display:flex;justify-content:space-between;align-items:center}" +
    ".cai-head button{background:none;border:none;color:#fff;font-size:18px;cursor:pointer}" +
    ".cai-log{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}" +
    ".cai-msg{max-width:85%;padding:8px 12px;border-radius:12px;white-space:pre-wrap}" +
    ".cai-msg.user{align-self:flex-end;background:" + COLOR + ";color:#fff}" +
    ".cai-msg.bot{align-self:flex-start;background:rgba(148,163,216,.15);border:1px solid rgba(165,180,235,.2)}" +
    ".cai-card{align-self:stretch;border:1px solid rgba(165,180,235,.25);border-radius:12px;padding:10px 12px;background:rgba(148,163,216,.08)}" +
    ".cai-card b{display:block}" +
    ".cai-card small{color:#a5b1d6}" +
    ".cai-card .cai-actions{margin-top:6px;display:flex;gap:6px}" +
    ".cai-card a,.cai-card button{font-size:12px;padding:4px 10px;border-radius:999px;border:1px solid " + COLOR + ";color:#fff;background:transparent;cursor:pointer;text-decoration:none}" +
    ".cai-form{display:flex;gap:8px;padding:12px;border-top:1px solid rgba(165,180,235,.2)}" +
    ".cai-form input{flex:1;padding:10px 12px;border-radius:10px;border:1px solid rgba(165,180,235,.3);background:rgba(7,11,23,.6);color:#eef2ff}" +
    ".cai-form button{padding:10px 16px;border-radius:10px;border:none;background:" + COLOR + ";color:#fff;font-weight:700;cursor:pointer}" +
    ".cai-form button:disabled{opacity:.5}";
  document.head.appendChild(style);

  /* ---------- DOM ---------- */
  var button = document.createElement("button");
  button.className = "cai-btn";
  button.setAttribute("aria-label", TITLE);
  button.innerHTML = "&#128172;";

  var panel = document.createElement("div");
  panel.className = "cai-panel";
  panel.dir = DIR;
  panel.innerHTML =
    '<div class="cai-head"><span>' + TITLE + '</span><button type="button" aria-label="close">×</button></div>' +
    '<div class="cai-log" role="log" aria-live="polite"></div>' +
    '<form class="cai-form"><input type="text" maxlength="2000" placeholder="اكتب سؤالك…" aria-label="سؤالك" required />' +
    '<button type="submit">إرسال</button></form>';

  document.body.appendChild(button);
  document.body.appendChild(panel);

  var log = panel.querySelector(".cai-log");
  var form = panel.querySelector(".cai-form");
  var input = panel.querySelector("input");
  var send = panel.querySelector(".cai-form button");
  var greeted = false;

  function addMessage(text, who) {
    var element = document.createElement("div");
    element.className = "cai-msg " + who;
    element.textContent = text;
    log.appendChild(element);
    log.scrollTop = log.scrollHeight;
    return element;
  }

  function addProductCard(item) {
    var card = document.createElement("div");
    card.className = "cai-card";
    var stockText = item.product.stock > 0 ? "متوفر" : "غير متوفر";
    card.innerHTML = "<b></b><small></small><div class='cai-actions'></div>";
    card.querySelector("b").textContent = item.product.name + " — " + item.product.price + " ج.م";
    card.querySelector("small").textContent = stockText + (item.reasons && item.reasons[0] ? " · " + item.reasons[0] : "");
    var actions = card.querySelector(".cai-actions");
    if (URL_TEMPLATE) {
      var link = document.createElement("a");
      link.href = URL_TEMPLATE.replace("{id}", encodeURIComponent(item.product_id));
      link.target = "_blank"; link.rel = "noopener";
      link.textContent = "عرض المنتج";
      actions.appendChild(link);
    }
    if (typeof window.CommerceAIOnAddToCart === "function") {
      var cartButton = document.createElement("button");
      cartButton.type = "button";
      cartButton.textContent = "أضف للسلة";
      cartButton.addEventListener("click", function () {
        cartButton.disabled = true;
        cartButton.textContent = "جارٍ الإضافة…";
        Promise.resolve(window.CommerceAIOnAddToCart(item.product_id, item.product))
          .then(function (result) {
            var succeeded = result === true || (result && result.success === true);
            if (!succeeded) throw new Error("cart_callback_failed");
            return track("add_to_cart", {
              product_id: item.product_id,
              payload: { source: "widget" },
            });
          })
          .then(function () { cartButton.textContent = "تمت الإضافة ✓"; })
          .catch(function () {
            cartButton.textContent = "تعذر الإضافة";
            cartButton.disabled = false;
          });
      });
      actions.appendChild(cartButton);
    }
    log.appendChild(card);
    log.scrollTop = log.scrollHeight;
  }

  function toggle(open) {
    panel.classList.toggle("open", open);
    if (open && !greeted) {
      greeted = true;
      addMessage("أهلًا! اسألني عن المنتجات أو الأسعار أو سياسات المتجر.", "bot");
    }
    if (open) input.focus();
  }

  button.addEventListener("click", function () { toggle(!panel.classList.contains("open")); });
  panel.querySelector(".cai-head button").addEventListener("click", function () { toggle(false); });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    addMessage(text, "user");
    input.value = "";
    send.disabled = true;
    var pending = addMessage("…", "bot");
    post("/api/v1/public/chat", {
      session_key: sessionKey,
      message: text,
      page_url: location.href.slice(0, 500),
    }).then(function (response) {
      pending.textContent = response.reply;
      (response.recommendations || []).forEach(addProductCard);
    }).catch(function () {
      pending.textContent = "تعذر الاتصال بالمساعد حاليًا. حاول مرة أخرى.";
    }).finally(function () {
      send.disabled = false;
      input.focus();
    });
  });

  window.CommerceAIWidget = {
    track: track,
    setConsent: function (value) {
      consented = value === true;
      if (consented && TRACK === "auto") {
        return track("page_view", { payload: { path: location.pathname.slice(0, 200) } });
      }
      return Promise.resolve({ consented: consented });
    },
    open: function () { toggle(true); },
    close: function () { toggle(false); },
    sessionKey: sessionKey,
  };
})();
