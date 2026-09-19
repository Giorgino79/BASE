from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from fatturazione_attiva.models import Fattura, NotaCredito

from .models import ContoContabile, MovimentoPrimaNota


def _fattura(numero, progressivo, imponibile):
    imponibile = Decimal(imponibile)
    iva = (imponibile * Decimal('0.22')).quantize(Decimal('0.01'))
    return Fattura.objects.create(
        anno=2026, progressivo=progressivo, numero=numero,
        data_emissione=date(2026, 9, 1), dest_nome='AVR SPA',
        imponibile=imponibile, importo_iva=iva, totale=imponibile + iva,
    )


# Senza manifest statico (collectstatic) il render delle pagine d'errore fallirebbe.
@override_settings(STORAGES={
    'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class IncassoConNotaCreditoTest(TestCase):
    """Il cliente paga al netto di una NC: va scelta nel select delle fatture."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='t', password='x')
        self.client.force_login(self.user)
        self.banca = ContoContabile.objects.create(tipo=ContoContabile.Tipo.BANCA, nome='Banca')
        self.f1 = _fattura('FA-2026-0001', 1, '1000.00')   # totale 1220,00
        self.f2 = _fattura('FA-2026-0002', 2, '200.00')    # totale 244,00
        self.nc = NotaCredito.crea(self.f1, Decimal('100.00'), 'reso', self.user)  # 122,00

    def _post(self, fatture, importo, **quote):
        dati = {'controparte': 'AVR SPA', 'fatture': fatture, 'importo': importo,
                'data': '2026-09-19', 'conto': self.banca.pk, 'note': ''}
        dati.update(quote)
        return self.client.post(reverse('contabilita:incasso_create'), dati)

    def test_endpoint_elenca_la_nota_credito_con_importo_negativo(self):
        r = self.client.get(reverse('contabilita:incasso_fatture'), {'controparte': 'AVR SPA'})
        nc = [x for x in r.json()['results'] if x.get('tipo') == 'nc']
        self.assertEqual(len(nc), 1)
        self.assertEqual(nc[0]['id'], f'nc_{self.nc.pk}')
        self.assertEqual(Decimal(nc[0]['totale']), Decimal('-122.00'))

    def test_incasso_al_netto_della_nota(self):
        # 1220 + 244 - 122 = 1342 ricevuti
        r = self._post([self.f1.pk, self.f2.pk, f'nc_{self.nc.pk}'], '1342.00')
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['form'].errors)
        self.f1.refresh_from_db(); self.f2.refresh_from_db(); self.nc.refresh_from_db()
        self.assertEqual(self.f1.stato, Fattura.Stato.PAGATA)
        self.assertEqual(self.f2.stato, Fattura.Stato.PAGATA)
        self.assertTrue(self.nc.compensata)
        incassi = MovimentoPrimaNota.objects.filter(tipo=MovimentoPrimaNota.Tipo.INCASSO)
        self.assertEqual(sorted(m.importo for m in incassi),
                         [Decimal('244.00'), Decimal('1098.00')])

    def test_senza_nc_l_importo_pieno_non_quadra(self):
        r = self._post([self.f1.pk, self.f2.pk, f'nc_{self.nc.pk}'], '1464.00')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(MovimentoPrimaNota.objects.filter(
            tipo=MovimentoPrimaNota.Tipo.INCASSO).exists())

    def test_nc_senza_la_sua_fattura_e_rifiutata(self):
        r = self._post([self.f2.pk, f'nc_{self.nc.pk}'], '122.00')
        self.assertEqual(r.status_code, 200)
        self.nc.refresh_from_db()
        self.assertFalse(self.nc.compensata)

    def test_nc_gia_compensata_non_e_piu_offerta(self):
        self._post([self.f1.pk, f'nc_{self.nc.pk}'], '1098.00')
        # f1 è saldata: né lei né la sua NC compaiono ancora
        r = self.client.get(reverse('contabilita:incasso_fatture'), {'controparte': 'AVR SPA'})
        self.assertEqual([x['numero'] for x in r.json()['results']], ['FA-2026-0002'])
