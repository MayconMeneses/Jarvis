"""sounddevice de mentira: grava o que seria tocado, sem placa de som."""

import types


def sd_falso(falha_abrir=0, ordem=None):
    """Retorna (módulo, registro). `falha_abrir`: quantas aberturas de OutputStream falham (placa sumiu)."""
    registro = types.SimpleNamespace(fluxos=[], aberturas=0, reinicios=0, ordem=ordem if ordem is not None else [])

    class OutputStream:
        def __init__(self, samplerate, channels, dtype, latency=None):
            registro.aberturas += 1
            if registro.aberturas <= falha_abrir:
                raise OSError("Error opening OutputStream: dispositivo indisponível")
            self.taxa, self.escritos, self.abortou = samplerate, [], 0
            registro.fluxos.append(self)

        def start(self):
            pass

        def write(self, bloco):
            if not self.escritos:
                registro.ordem.append("play")
            self.escritos.append(bloco.copy())

        def abort(self):
            self.abortou += 1

        def close(self):
            pass

    def reiniciar():
        registro.reinicios += 1

    modulo = types.SimpleNamespace(
        OutputStream=OutputStream, _terminate=reiniciar, _initialize=lambda: None,
        play=lambda *a, **k: registro.ordem.append("chime"), wait=lambda: None, stop=lambda: None)
    return modulo, registro
