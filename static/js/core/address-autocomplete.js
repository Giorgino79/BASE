/**
 * Autocomplete indirizzi riutilizzabile (Google Places).
 *
 * Attivazione: aggiungere all'input "indirizzo" di un form l'attributo
 * data-rattus-address con un JSON che indica gli id degli input collegati:
 *   {"citta": "id_citta", "cap": "id_cap", "provincia": "id_provincia",
 *    "lat": "id_latitudine", "lng": "id_longitudine"}
 * Tutte le chiavi sono opzionali: se citta/cap/provincia sono assenti (es.
 * indirizzo libero senza campi separati) l'input viene riempito con
 * l'indirizzo formattato completo restituito da Google.
 *
 * Caricato globalmente in base.html; si attiva da solo quando la Google Maps
 * JavaScript API (libraries=places) chiama initRattusAddressAutocomplete.
 */
function initRattusAddressAutocomplete() {
  if (!window.google || !google.maps || !google.maps.places) return;

  // Evento globale: qualunque pagina può agganciarsi per sapere quando la
  // Google Maps JavaScript API è pronta (es. per inizializzare una mappa propria),
  // senza dover fare polling su window.google.
  window.dispatchEvent(new Event('rattus:maps-ready'));

  document.querySelectorAll('[data-rattus-address]').forEach(function (input) {
    if (input.dataset.rattusAddressInit) return;
    input.dataset.rattusAddressInit = '1';

    var cfg;
    try {
      cfg = JSON.parse(input.dataset.rattusAddress);
    } catch (e) {
      return;
    }

    var autocomplete = new google.maps.places.Autocomplete(input, {
      componentRestrictions: { country: 'it' },
      fields: ['address_components', 'formatted_address', 'geometry'],
    });

    autocomplete.addListener('place_changed', function () {
      var place = autocomplete.getPlace();
      if (!place || !place.geometry) return;

      if (cfg.lat) {
        var latEl = document.getElementById(cfg.lat);
        if (latEl) latEl.value = place.geometry.location.lat();
      }
      if (cfg.lng) {
        var lngEl = document.getElementById(cfg.lng);
        if (lngEl) lngEl.value = place.geometry.location.lng();
      }

      var hasComponentTargets = cfg.citta || cfg.cap || cfg.provincia;
      if (!hasComponentTargets) {
        input.value = place.formatted_address;
        return;
      }

      var comp = {};
      (place.address_components || []).forEach(function (c) {
        c.types.forEach(function (t) { comp[t] = c; });
      });

      var via = (comp.route ? comp.route.long_name : '') +
                (comp.street_number ? ' ' + comp.street_number.long_name : '');
      input.value = via.trim() || place.formatted_address;

      if (cfg.citta) {
        var cittaEl = document.getElementById(cfg.citta);
        var cittaComp = comp.locality || comp.postal_town || comp.administrative_area_level_3;
        if (cittaEl && cittaComp) cittaEl.value = cittaComp.long_name;
      }
      if (cfg.cap) {
        var capEl = document.getElementById(cfg.cap);
        if (capEl && comp.postal_code) capEl.value = comp.postal_code.long_name;
      }
      if (cfg.provincia) {
        var provEl = document.getElementById(cfg.provincia);
        if (provEl && comp.administrative_area_level_2) provEl.value = comp.administrative_area_level_2.short_name;
      }
    });
  });
}

window.initRattusAddressAutocomplete = initRattusAddressAutocomplete;
