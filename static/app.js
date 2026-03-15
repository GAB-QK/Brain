/**
 * Alpine.js — logique de l'interface web du Carnet de lecture.
 * Gère l'analyse, l'import dans Obsidian, et l'affichage progressif.
 */

document.addEventListener('alpine:init', () => {
  Alpine.data('app', () => ({

    // ── État ────────────────────────────────────────────────────────────
    darkMode:    true,
    backend:     'obsidian',
    note:        '',
    loading:     false,
    analyzed:    false,
    importing:   false,
    imported:    false,
    data:        null,
    ch_num:      null,
    previewFiles: [],
    files:       [],
    books:       [],
    toast:       null,
    _toastTimer: null,

    // Révélation progressive des sections
    showSummary:     false,
    showPersonnages: false,
    showThemes:      false,
    showCitations:   false,
    showWarnings:    false,
    showFiles:       false,
    showImportBtn:   false,

    // ── Initialisation ──────────────────────────────────────────────────
    init() {
      document.documentElement.setAttribute('data-theme', 'dark');
      this.fetchStatus();
      this.fetchConfig();
    },

    // ── Dark mode ───────────────────────────────────────────────────────
    toggleDarkMode() {
      this.darkMode = !this.darkMode;
      document.documentElement.setAttribute('data-theme', this.darkMode ? 'dark' : 'light');
    },

    // ── Config (backend actif) ───────────────────────────────────────────
    async fetchConfig() {
      try {
        const res  = await fetch('/config');
        const json = await res.json();
        this.backend = json.backend || 'obsidian';
      } catch (_) {
        // silencieux — pas critique
      }
    },

    // ── Vault status ────────────────────────────────────────────────────
    async fetchStatus() {
      try {
        const res  = await fetch('/status');
        const json = await res.json();
        this.books = json.books || [];
      } catch (_) {
        // silencieux — pas critique
      }
    },

    // ── Analyse ─────────────────────────────────────────────────────────
    async analyze() {
      if (this.loading || !this.note.trim()) return;

      this.loading      = true;
      this.analyzed     = false;
      this.imported     = false;
      this.data         = null;
      this.previewFiles = [];
      this.files        = [];
      this._resetReveal();

      try {
        const res  = await fetch('/analyze', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ note: this.note }),
        });
        const json = await res.json();

        if (!res.ok) {
          this._toast('❌ ' + (json.error || "Erreur lors de l'analyse."), 'error');
          return;
        }

        this.data         = json.data;
        this.ch_num       = json.ch_num;
        this.previewFiles = json.preview_files || [];

        await this._revealProgressively();
        this.analyzed = true;

      } catch (err) {
        this._toast('❌ Erreur réseau : ' + err.message, 'error');
      } finally {
        this.loading = false;
      }
    },

    // ── Révélation progressive ──────────────────────────────────────────
    async _revealProgressively() {
      const wait = ms => new Promise(r => setTimeout(r, ms));

      this.showSummary     = true;  await wait(150);
      this.showPersonnages = true;  await wait(150);
      this.showThemes      = true;  await wait(150);
      this.showCitations   = true;  await wait(150);
      this.showWarnings    = true;  await wait(150);
      this.showFiles       = true;  await wait(250);
      this.showImportBtn   = true;
    },

    _resetReveal() {
      this.showSummary = this.showPersonnages = this.showThemes =
      this.showCitations = this.showWarnings = this.showFiles =
      this.showImportBtn = false;
    },

    // ── Import ──────────────────────────────────────────────────────────
    async importVault() {
      if (this.importing || this.imported || !this.data) return;
      this.importing = true;

      try {
        const res  = await fetch('/import', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ data: this.data, ch_num: this.ch_num }),
        });
        const json = await res.json();

        if (!res.ok) {
          this._toast('❌ ' + (json.error || "Erreur lors de l'import."), 'error');
          return;
        }

        this.files    = json.files || [];
        this.imported = true;
        await this.fetchStatus();

        const n = this.files.length;
        this._toast(`✅ Vault mis à jour — ${n}\u202ffichier${n > 1 ? 's' : ''}`, 'success');

      } catch (err) {
        this._toast('❌ Erreur réseau : ' + err.message, 'error');
      } finally {
        this.importing = false;
      }
    },

    // ── Toast ───────────────────────────────────────────────────────────
    _toast(message, type = 'info') {
      if (this._toastTimer) clearTimeout(this._toastTimer);
      this.toast = { message, type };
      this._toastTimer = setTimeout(() => { this.toast = null; }, 4500);
    },

    // ── Markdown ────────────────────────────────────────────────────────
    renderMarkdown(text) {
      if (!text) return '';
      try {
        const md = window.markdownit({ breaks: true, linkify: false });
        return md.render(String(text));
      } catch (_) {
        return String(text);
      }
    },

  }));
});
