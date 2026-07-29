class CydUiPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._status = null;
    this._loading = false;
  }

  set hass(value) {
    this._hass = value;
    if (!this._status && !this._loading) this._loadStatus();
  }

  set narrow(value) {
    this.toggleAttribute("narrow", Boolean(value));
  }

  set panel(value) {
    this._panel = value;
  }

  async _loadStatus() {
    if (!this._hass) return;
    this._loading = true;
    try {
      this._status = await this._hass.callWS({ type: "cyd_ui/status" });
    } catch (error) {
      this._status = { ready: false, message: String(error) };
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _render() {
    const status = this._status;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; min-height:100%; background:var(--primary-background-color); color:var(--primary-text-color); }
        main { max-width:920px; margin:0 auto; padding:32px 20px; }
        h1 { margin:0 0 8px; font-size:30px; }
        .subtitle { color:var(--secondary-text-color); margin:0 0 28px; }
        .card { background:var(--card-background-color); border-radius:16px; padding:24px; box-shadow:var(--ha-card-box-shadow); }
        .state { display:flex; align-items:center; gap:12px; font-weight:600; }
        .dot { width:12px; height:12px; border-radius:50%; background:${status?.ready ? "#2e7d32" : "#c62828"}; }
        .next { margin-top:22px; padding-top:18px; border-top:1px solid var(--divider-color); color:var(--secondary-text-color); }
      </style>
      <main>
        <h1>CYD UI</h1>
        <p class="subtitle">Motor de interfaces para paneles ESPHome + LVGL</p>
        <section class="card">
          <div class="state"><span class="dot"></span><span>${status?.message || "Conectando con Home Assistant…"}</span></div>
          <p>Versión: ${status?.version || "0.1.0"}</p>
          <p class="next">Próximo paso: trasladar aquí el editor de páginas, entidades y configuración del dispositivo.</p>
        </section>
      </main>`;
  }

  connectedCallback() {
    this._render();
  }
}

if (!customElements.get("cyd-ui-panel")) {
  customElements.define("cyd-ui-panel", CydUiPanel);
}
