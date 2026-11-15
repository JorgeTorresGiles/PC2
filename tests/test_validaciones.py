import unittest
from validaciones import monto_a_centimos, validar_fecha, validar_descripcion, validar_filtros, importe


class ValidacionesTests(unittest.TestCase):
    def test_monto_decimal(self):
        self.assertEqual(monto_a_centimos("12.50"), 1250)
        self.assertEqual(monto_a_centimos("12,50"), 1250)
        self.assertEqual(monto_a_centimos("0.01"), 1)

    def test_monto_invalido(self):
        for valor in ("0", "-5", "1.234", "hola", "", "1e6"):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                monto_a_centimos(valor)

    def test_fecha_invalida(self):
        with self.assertRaises(ValueError):
            validar_fecha("2026-02-31")

    def test_fecha_valida(self):
        self.assertEqual(validar_fecha("2026-11-11"), "2026-11-11")

    def test_filtros(self):
        with self.assertRaises(ValueError):
            validar_filtros("2026-11-11", "2026-01-01")

    def test_descripcion(self):
        self.assertEqual(validar_descripcion("  Pago   de luz "), "Pago de luz")
        with self.assertRaises(ValueError):
            validar_descripcion("ok")

    def test_formato(self):
        self.assertEqual(importe(1750), "17.50")


if __name__ == '__main__':
    unittest.main()
