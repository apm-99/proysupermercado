import re
import textdistance

class ComparadorProductos:
    def extraer_volumen(self, texto):
        texto = texto.lower()
        patrones = [
            (r"(\d+(?:[\.,]\d+)?)(?:\s*)?(ml|cc)", 1),
            (r"(\d+(?:[\.,]\d+)?)(?:\s*)?(litros|lt|l)", 1000),
        ]
        for patron, factor in patrones:
            match = re.search(patron, texto)
            if match:
                cantidad = float(match.group(1).replace(',', '.'))
                return int(cantidad * factor)
        return None


    def extraer_unidades(self, texto):
        texto = texto.lower()
        patrones = [
            r"(?:x|\bpack\b|\bpaquete\b|\bunidades\b|\bu\b|\buds\b)[^\d]*(\d+)",
            r"(\d+)\s*(?:x|\bunidades|\bu|\buds)"
        ]
        for patron in patrones:
            match = re.search(patron, texto)
            if match:
                return int(match.group(1))
        return 1

    def limpiar_texto(self, texto):
        texto = texto.lower()
        texto = texto.replace('cc', 'ml')

        # Convertir volumen en litros a ml directamente en el texto
        def reemplazo_volumen(match):
            cantidad = float(match.group(1).replace(',', '.'))
            ml = int(cantidad * 1000)
            return f"{ml}ml"

        texto = re.sub(r"(\d+(?:[\.,]\d+)?)(?:\s*)?(litros|lt|l)", reemplazo_volumen, texto)

        # Eliminar palabras irrelevantes
        texto = re.sub(r"\b(botella|pack|unidad|envase|cerveza|lata|origen)\b", "", texto)

        # Eliminar signos y espacios extra
        texto = re.sub(r"[^\w\s]", " ", texto)
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()


    def comparar(self, producto_a, producto_b):
        texto_a = self.limpiar_texto(producto_a)
        texto_b = self.limpiar_texto(producto_b)

        vol_a = self.extraer_volumen(producto_a)
        vol_b = self.extraer_volumen(producto_b)

        unid_a = self.extraer_unidades(producto_a)
        unid_b = self.extraer_unidades(producto_b)

        if vol_a != vol_b or unid_a != unid_b:
            return False

        score = textdistance.ratcliff_obershelp.normalized_similarity(texto_a, texto_b)
        print(f"[DEBUG] score: {score}")
        return score > 0.9
    
# comparador = ComparadorProductos()
# print(comparador.comparar("Cerveza Andes Roja 473ml",
# "Cerveza Andes Rubia 473ml"))

# pares = [
#    ("Fernet Branca 1l", "Fernet Buhero 750ml"),
#    ("Fernet Branca 1L", "Fernet Branca 452ml")
# ]

# for a, b in pares:
#     resultado = comparador.comparar(a, b)
#     print(f"Comparar:\n → {a}\n → {b}\n = {resultado}\n")
