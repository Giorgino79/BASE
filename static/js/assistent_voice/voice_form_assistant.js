/**
 * VoiceFormAssistant — Assistente vocale per form Django
 * =======================================================
 * Legge ad alta voce le etichette dei campi di un form, una alla volta,
 * ascolta la risposta dell'utente, compila il campo e passa al successivo.
 * Al termine chiede conferma e invia il form.
 *
 * Requisiti: browser Chromium (Chrome/Edge) + HTTPS (o localhost).
 * Lingua: italiano (it-IT).
 *
 * Uso minimo:
 *   const va = new VoiceFormAssistant('#form-cliente');
 *   document.querySelector('#btn-voce').addEventListener('click', () => va.start());
 *
 * Comandi vocali disponibili durante la compilazione:
 *   "ripeti"    → rilegge la domanda corrente
 *   "indietro"  → torna al campo precedente
 *   "salta"     → lascia vuoto il campo e va avanti (solo campi non obbligatori)
 *   "annulla"   → interrompe l'assistente
 *   Alla conferma finale: "sì / conferma" oppure "no / annulla"
 */
class VoiceFormAssistant {
  constructor(formSelector, options = {}) {
    this.form = document.querySelector(formSelector);
    if (!this.form) throw new Error(`Form non trovato: ${formSelector}`);

    this.opts = Object.assign({
      lang: 'it-IT',
      rate: 1.0,            // velocità di lettura
      confirmBeforeSubmit: true,
      readBackValue: true,  // rilegge il valore riconosciuto
      statusWidget: true,   // mostra il widget di stato flottante
    }, options);

    this.synth = window.speechSynthesis;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.supported = !!(SR && this.synth);
    this.SR = SR;

    this.fields = [];
    this.index = 0;
    this.active = false;
    this.widget = null;
  }

  /* ---------- API pubblica ---------- */

  async start() {
    if (!this.supported) {
      alert('Il riconoscimento vocale non è supportato da questo browser. Usa Chrome o Edge.');
      return;
    }
    if (this.active) return;
    this.active = true;
    this._collectFields();
    if (this.opts.statusWidget) this._buildWidget();
    this.index = 0;

    await this._speak('Iniziamo la compilazione del modulo.');
    await this._loop();
  }

  stop() {
    this.active = false;
    this.synth.cancel();
    if (this.recognition) try { this.recognition.abort(); } catch (e) {}
    this._removeWidget();
  }

  /* ---------- Ciclo principale ---------- */

  async _loop() {
    while (this.active && this.index < this.fields.length) {
      const field = this.fields[this.index];
      const question = this._questionFor(field);
      this._setStatus(`🔊 ${question}`);
      field.el.focus();
      field.el.scrollIntoView({ behavior: 'smooth', block: 'center' });

      await this._speak(question);
      if (!this.active) return;

      this._setStatus('🎤 In ascolto…');
      let answer;
      try {
        answer = await this._listen();
      } catch (e) {
        await this._speak('Non ho sentito nulla. Ripeto la domanda.');
        continue;
      }
      if (!this.active) return;

      const cmd = answer.trim().toLowerCase();

      // --- comandi di navigazione ---
      if (cmd === 'ripeti') continue;
      if (cmd === 'indietro') {
        this.index = Math.max(0, this.index - 1);
        continue;
      }
      if (cmd === 'annulla') {
        await this._speak('Compilazione annullata.');
        this.stop();
        return;
      }
      if (cmd === 'salta') {
        if (field.el.required) {
          await this._speak('Questo campo è obbligatorio, non posso saltarlo.');
          continue;
        }
        this.index++;
        continue;
      }

      // --- compilazione del campo ---
      const ok = await this._fillField(field, answer);
      if (!ok) continue; // es. opzione select non riconosciuta: ripete

      if (this.opts.readBackValue) {
        await this._speak(`Ho scritto: ${this._displayValue(field)}.`);
      }
      this.index++;
    }

    if (this.active) await this._finish();
  }

  async _finish() {
    if (this.opts.confirmBeforeSubmit) {
      await this._speak('Modulo completato. Vuoi salvare? Rispondi sì o no.');
      this._setStatus('🎤 Confermi il salvataggio?');
      let answer = '';
      try { answer = (await this._listen()).toLowerCase(); } catch (e) {}

      if (/(^|\s)(sì|si|conferma|salva|ok)(\s|$)/.test(answer)) {
        await this._speak('Salvataggio in corso.');
        this.stop();
        this.form.requestSubmit ? this.form.requestSubmit() : this.form.submit();
      } else {
        await this._speak('Va bene, non salvo. Puoi rivedere il modulo manualmente.');
        this.stop();
      }
    } else {
      this.stop();
      this.form.requestSubmit ? this.form.requestSubmit() : this.form.submit();
    }
  }

  /* ---------- Raccolta e compilazione campi ---------- */

  _collectFields() {
    const els = this.form.querySelectorAll('input, select, textarea');
    this.fields = [];
    els.forEach(el => {
      const type = (el.type || '').toLowerCase();
      if (['hidden', 'submit', 'button', 'file', 'image', 'reset'].includes(type)) return;
      if (el.disabled || el.readOnly) return;
      if (el.name === 'csrfmiddlewaretoken') return;
      if (el.offsetParent === null) return; // non visibile

      this.fields.push({ el, label: this._labelFor(el), type: el.tagName === 'SELECT' ? 'select' : type || el.tagName.toLowerCase() });
    });
  }

  _labelFor(el) {
    if (el.id) {
      const lab = this.form.querySelector(`label[for="${el.id}"]`);
      if (lab) return lab.textContent.replace('*', '').trim();
    }
    const parentLab = el.closest('label');
    if (parentLab) return parentLab.textContent.replace('*', '').trim();
    return el.getAttribute('placeholder') || el.name.replace(/_/g, ' ');
  }

  _questionFor(field) {
    if (field.type === 'checkbox') return `${field.label}? Rispondi sì o no.`;
    if (field.type === 'select') return `${field.label}?`;
    return `${field.label}?`;
  }

  async _fillField(field, answer) {
    const el = field.el;

    if (field.type === 'checkbox') {
      el.checked = /(^|\s)(sì|si|vero|certo)(\s|$)/i.test(answer);
      this._fireEvents(el);
      return true;
    }

    if (field.type === 'select') {
      const options = Array.from(el.options).filter(o => o.value !== '');
      const norm = answer.toLowerCase().trim();
      let match = options.find(o => o.textContent.toLowerCase().trim() === norm)
               || options.find(o => o.textContent.toLowerCase().includes(norm))
               || options.find(o => norm.includes(o.textContent.toLowerCase().trim()));
      if (!match) {
        const list = options.slice(0, 8).map(o => o.textContent.trim()).join(', ');
        await this._speak(`Non ho trovato questa opzione. Le scelte disponibili sono: ${list}.`);
        return false;
      }
      el.value = match.value;
      this._fireEvents(el);
      return true;
    }

    let value = answer;
    if (field.type === 'email') {
      // "mario punto rossi chiocciola esempio punto it" → mario.rossi@esempio.it
      value = value.toLowerCase()
        .replace(/\s*chiocciola\s*/g, '@')
        .replace(/\s*punto\s*/g, '.')
        .replace(/\s*trattino basso\s*/g, '_')
        .replace(/\s*trattino\s*/g, '-')
        .replace(/\s+/g, '');
    }
    if (field.type === 'tel' || field.type === 'number') {
      value = value.replace(/\s+/g, '');
    }
    if (field.type === 'date') {
      const d = this._parseItalianDate(value);
      if (!d) {
        await this._speak('Non ho capito la data. Ripeti, ad esempio: dodici giugno duemila ventisei.');
        return false;
      }
      value = d;
    }

    el.value = value;
    this._fireEvents(el);
    return true;
  }

  _parseItalianDate(text) {
    // Il riconoscimento vocale di solito restituisce già "12 giugno 2026" o "12/06/2026"
    const slash = text.match(/(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})/);
    if (slash) {
      let [, d, m, y] = slash;
      if (y.length === 2) y = '20' + y;
      return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
    }
    const mesi = ['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'];
    const m2 = text.toLowerCase().match(new RegExp(`(\\d{1,2})\\s+(${mesi.join('|')})\\s+(\\d{4})`));
    if (m2) {
      const month = String(mesi.indexOf(m2[2]) + 1).padStart(2, '0');
      return `${m2[3]}-${month}-${String(m2[1]).padStart(2, '0')}`;
    }
    return null;
  }

  _displayValue(field) {
    if (field.type === 'checkbox') return field.el.checked ? 'sì' : 'no';
    if (field.type === 'select') return field.el.selectedOptions[0]?.textContent.trim() || '';
    return field.el.value;
  }

  _fireEvents(el) {
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  /* ---------- Voce: sintesi e riconoscimento ---------- */

  _speak(text) {
    return new Promise(resolve => {
      this.synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = this.opts.lang;
      u.rate = this.opts.rate;
      const itVoice = this.synth.getVoices().find(v => v.lang.startsWith('it'));
      if (itVoice) u.voice = itVoice;
      u.onend = resolve;
      u.onerror = resolve;
      this.synth.speak(u);
    });
  }

  _listen() {
    return new Promise((resolve, reject) => {
      const rec = new this.SR();
      this.recognition = rec;
      rec.lang = this.opts.lang;
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      let got = false;

      rec.onresult = e => {
        got = true;
        resolve(e.results[0][0].transcript);
      };
      rec.onerror = e => reject(e.error);
      rec.onend = () => { if (!got) reject('no-speech'); };
      rec.start();
    });
  }

  /* ---------- Widget di stato ---------- */

  _buildWidget() {
    this._removeWidget();
    const w = document.createElement('div');
    w.id = 'vfa-widget';
    w.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;background:#212529;color:#fff;' +
      'padding:12px 16px;border-radius:10px;box-shadow:0 4px 14px rgba(0,0,0,.3);font-size:14px;max-width:320px;display:flex;align-items:center;gap:10px;';
    w.innerHTML = '<span id="vfa-status">Avvio assistente vocale…</span>' +
      '<button id="vfa-stop" style="background:#dc3545;border:none;color:#fff;border-radius:6px;padding:4px 10px;cursor:pointer;">Stop</button>';
    document.body.appendChild(w);
    w.querySelector('#vfa-stop').addEventListener('click', () => this.stop());
    this.widget = w;
  }

  _setStatus(text) {
    const s = document.getElementById('vfa-status');
    if (s) s.textContent = text;
  }

  _removeWidget() {
    if (this.widget) { this.widget.remove(); this.widget = null; }
  }
}

window.VoiceFormAssistant = VoiceFormAssistant;
