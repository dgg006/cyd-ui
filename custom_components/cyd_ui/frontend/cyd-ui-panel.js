const STATIC_ROOT = "/cyd_ui_static";
const ASSET_VERSION = "0.2.7";

function describeError(error) {
  if (typeof error === "string") return error;
  if (error?.message) return error.message;
  if (error?.code) return `${error.code}${error.message ? `: ${error.message}` : ""}`;
  try {
    return JSON.stringify(error);
  } catch (_ignored) {
    return String(error);
  }
}

const EDITOR_MARKUP = `
  <header class="topbar">
    <div><div class="eyebrow">CYD UI ENGINE · v${ASSET_VERSION}</div><h1>Configurador</h1></div>
    <div class="top-actions">
      <span id="connectionState" class="status neutral">Iniciando…</span>
      <button id="nativeBridgeButton" class="button secondary">Puente</button>
      <button id="reloadButton" class="button secondary hidden">Recargar pantalla</button>
      <button id="saveButton" class="button primary">Guardar en Home Assistant</button>
    </div>
  </header>
  <main class="workspace">
    <aside class="pages-panel panel">
      <div class="panel-heading"><div><span class="section-kicker">ESTRUCTURA</span><h2>Páginas</h2></div><button id="addPageButton" class="icon-button" title="Agregar página">+</button></div>
      <div id="pageList" class="page-list"></div><p class="hint">Arrastrá para ordenar. Máximo 8 páginas.</p>
      <button id="deviceSettingsButton" class="settings-card"><span class="settings-icon">⚙</span><span><strong>Configuración</strong><small>Pantalla, reposo y sonido</small></span></button>
    </aside>
    <section class="editor-panel panel">
      <div class="panel-heading"><div><span class="section-kicker">CONTENIDO</span><h2 id="editorTitle">Página</h2></div><div class="inline-actions"><button id="duplicateButton" class="text-button">Duplicar</button><button id="deleteButton" class="text-button danger">Eliminar</button></div></div>
      <div id="pageForm" class="page-form"></div>
      <div id="controlsHeading" class="controls-heading"><div><span class="section-kicker">CONTROLES</span><h3>Contenido de la página</h3></div><button id="addControlButton" class="button secondary hidden">Agregar valor</button></div>
      <div id="controlList" class="control-list"></div>
    </section>
    <aside class="preview-panel panel">
      <div class="panel-heading"><div><span class="section-kicker">VISTA PREVIA</span><h2>320 × 240</h2></div></div>
      <div id="devicePreview" class="device-preview"></div>
      <div class="entity-state"><span id="entityCount">Entidades: cargando…</span><button id="refreshEntitiesButton" class="text-button">Actualizar</button></div>
      <div id="validationBox" class="validation-box valid">Configuración lista.</div>
    </aside>
  </main>
  <div id="toast" class="toast hidden"></div>`;

class CydUiPanel extends HTMLElement {
  constructor() {
    super();
    this._root = this.attachShadow({ mode: "open" });
    this._hass = null;
    this._started = false;
    this._cleanup = null;
  }

  set hass(value) {
    this._hass = value;
    this._start();
  }

  set narrow(value) {
    this.toggleAttribute("narrow", Boolean(value));
  }

  set panel(value) {
    this._panel = value;
  }

  connectedCallback() {
    this._start();
  }

  disconnectedCallback() {
    if (this._cleanup) this._cleanup();
    this._cleanup = null;
    this._started = false;
  }

  async _start() {
    if (this._started || !this.isConnected || !this._hass) return;
    this._started = true;
    try {
      const status = await this._hass.callWS({ type: "cyd_ui/status" });
      if (!status.configured) {
        this._renderImport(status);
        return;
      }
      await this._renderEditor();
    } catch (error) {
      this._renderError(error);
    }
  }

  _baseStyle() {
    return `<style>
      :host { display:block; min-height:100%; background:var(--primary-background-color); color:var(--primary-text-color); }
      .bootstrap { max-width:760px; margin:0 auto; padding:40px 22px; }
      .bootstrap-card { background:var(--card-background-color); padding:26px; border-radius:16px; box-shadow:var(--ha-card-box-shadow); }
      .bootstrap button { border:0; border-radius:10px; padding:12px 18px; cursor:pointer; color:#fff; background:var(--primary-color); font-weight:700; }
      .bootstrap small { display:block; margin-top:14px; color:var(--secondary-text-color); }
    </style>`;
  }

  _renderImport(status) {
    this._root.innerHTML = `${this._baseStyle()}<main class="bootstrap"><section class="bootstrap-card">
      <h1>CYD UI</h1>
      <p>La integración está lista. Falta importar por única vez el proyecto que venimos desarrollando.</p>
      <button id="importCurrentProject">Importar proyecto actual</button>
      <small>Versión ${status.version}. El original local no será borrado.</small>
    </section></main>`;
    this._root.querySelector("#importCurrentProject").onclick = () => this._importCurrentProject();
  }

  async _importCurrentProject() {
    const button = this._root.querySelector("#importCurrentProject");
    button.disabled = true;
    button.textContent = "Importando…";
    try {
      const response = await fetch(`${STATIC_ROOT}/initial-project.json`, { cache: "no-store" });
      if (!response.ok) throw new Error(`No se pudo leer el proyecto: ${response.status}`);
      const project = await response.json();
      await this._hass.callWS({
        type: "cyd_ui/config/save",
        ui: project.ui,
        backend_map: project.backend_map,
      });
      await this._renderEditor();
    } catch (error) {
      button.disabled = false;
      button.textContent = "Reintentar importación";
      this._renderError(error);
    }
  }

  async _renderEditor() {
    this._root.innerHTML = `<link rel="stylesheet" href="${STATIC_ROOT}/editor.css?v=${ASSET_VERSION}">${EDITOR_MARKUP}`;
    const module = await import(`${STATIC_ROOT}/editor-app.js?v=${ASSET_VERSION}`);
    this._cleanup = module.startCydUiEditor(this._root, this._hass);
    await this._refreshBridgeButton();
  }

  async _refreshBridgeButton() {
    const button = this._root.querySelector("#nativeBridgeButton");
    if (!button) return;
    const status = await this._hass.callWS({ type: "cyd_ui/bridge/status" });
    button.textContent = status.enabled ? "Puente nativo activo" : "Migrar puente";
    button.onclick = async () => {
      const enabling = !status.enabled;
      const message = enabling
        ? "Esto desactivará las automatizaciones temporales y activará el puente nativo. ¿Continuar?"
        : "Esto detendrá el puente nativo y restaurará las automatizaciones temporales. ¿Continuar?";
      if (!window.confirm(message)) return;
      button.disabled = true;
      try {
        await this._hass.callWS({
          type: enabling ? "cyd_ui/bridge/migrate" : "cyd_ui/bridge/rollback",
        });
        await this._refreshBridgeButton();
      } catch (error) {
        button.disabled = false;
        window.alert(`No se pudo cambiar el puente: ${String(error)}`);
      }
    };
  }

  _renderError(error) {
    this._root.innerHTML = `${this._baseStyle()}<main class="bootstrap"><section class="bootstrap-card">
      <h1>No se pudo abrir CYD UI</h1><p id="errorMessage"></p>
    </section></main>`;
    this._root.querySelector("#errorMessage").textContent = describeError(error);
  }
}

if (!customElements.get("cyd-ui-panel")) {
  customElements.define("cyd-ui-panel", CydUiPanel);
}
