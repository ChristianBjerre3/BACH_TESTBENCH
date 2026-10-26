# Analyse: Auto-eksponering kan ikke slås fra (Raspberry Pi / Linux)

## 1. Problemstilling

På Raspberry Pi'en (Linux/V4L2-driverstakken) kan brugeren slå auto-eksponering fra i GUI'en
(`Control`-fanen), men kameraet forbliver reelt i automatisk eksponeringstilstand, og den
manuelle eksponerings-spinbox har ingen effekt på det virkelige billede.

Analysen er lavet som en **statisk kodegennemgang** (ingen kørende hardware-test), krydsrefereret
med den officielle V4L2/UVC-kontrolkonvention og OpenCV's dokumenterede backend-adfærd. Formålet
er at identificere *alle* kandidat-årsager i koden, rangere dem efter sandsynlighed/alvor, og give
konkrete diagnosticeringskommandoer til at be- eller afkræfte hver enkelt på selve Pi'en.

## 2. Metodevalg

| Trin | Metode | Begrundelse |
|---|---|---|
| 1 | Statisk kodeanalyse (manuel code review + `grep`) af `hardware/camera.py`, `gui/control_tab.py`, `gui/main_window.py` | Hurtigste vej til at finde logiske/syntaktiske fejl uden at kræve fysisk adgang til hardwaren i første omgang |
| 2 | Sammenligning af kodens antagelser med V4L2/UVC-specifikationen (kontrolnavne, værdikonventioner) og OpenCV's kendte backend-forskelle (DSHOW vs. V4L2) | Koden blander to forskellige værdikonventioner (DirectShow-floats vs. V4L2-heltal), hvilket er en kendt fejlkilde i cross-platform OpenCV-kode |
| 3 | Verifikation af eksterne afhængigheder (`requirements.txt`, `README.md`, hele repoet) for at se om `v4l2-ctl`/`v4l-utils` reelt er en dokumenteret/installeret afhængighed | Koden er 100 % afhængig af en ekstern binær (`v4l2-ctl`), som slet ikke er nævnt nogen steder i projektets opsætning |
| 4 | Opstilling af hypoteser rangeret efter sandsynlighed, med tilhørende empiriske testkommandoer der kan køres direkte på Pi'en | Da jeg ikke har live adgang til Pi'ens hardware, er næste skridt hypotesedrevet fejlfinding — I kan køre de vedlagte kommandoer og rapportere output, hvorefter den præcise årsag kan bekræftes |

Denne fremgangsmåde (statisk analyse → domæne-specifikationstjek → afhængighedsverifikation →
hypotesedrevet hardware-diagnosticering) kan bruges direkte som metodeafsnit i rapporten.

## 3. Relevante kodestier

- [testbench/hardware/camera.py](hardware/camera.py) — `set_auto_exposure()`, `get_auto_exposure()`, `_read_v4l2_control()`, `supports_auto_exposure()`
- [testbench/gui/control_tab.py](gui/control_tab.py) — checkbox/spinbox state (`_update_camera_control_state`)
- [testbench/gui/main_window.py](gui/main_window.py) — `_set_camera_auto_exposure()` (kalder camera-laget og synkroniserer GUI)

## 4. Fund, rangeret efter sandsynlighed

### Fund #1 (høj sandsynlighed): `v4l2-ctl` er ikke en dokumenteret/garanteret afhængighed

`set_auto_exposure()`, `set_exposure()` og `set_gain()` kalder alle eksternt program `v4l2-ctl`
via `subprocess.run(..., check=False, stderr=subprocess.DEVNULL)`
([camera.py L478-495](hardware/camera.py#L478-L495) m.fl.).

- `check=False` betyder at en fejlende kommando (fx "ukendt kontrol" eller "device busy") **ikke
  kaster en exception**.
- `stderr=subprocess.DEVNULL` skjuler enhver fejltekst fra driveren.
- `v4l2-ctl` (pakken `v4l-utils`) står **ikke** i [requirements.txt](requirements.txt) og er ikke
  nævnt i [README.md](README.md) eller andre steder i repoet (bekræftet ved søgning i hele
  workspacet).

**Konsekvens:** Hvis `v4l-utils` ikke er installeret på denne specifikke Pi (eller ikke er i PATH
for den bruger/service, der kører appen), bliver *alle* forsøg på at ændre auto-eksponering,
eksponering og gain til **stille no-ops** — koden fejler ikke synligt, men gør heller ikke noget.

**Diagnosticeringskommando (kør på Pi'en):**
```bash
which v4l2-ctl && v4l2-ctl --version
```
Hvis dette ikke returnerer en sti/version, er dette den primære årsag. Løsning:
```bash
sudo apt update && sudo apt install -y v4l-utils
```

### Fund #2 (bekræftet ved kodegennemgang): Parsing-fejl i `_read_v4l2_control()`

[camera.py L388-429](hardware/camera.py#L388-L429):

```python
pieces = line.split()
key = pieces[0].split("=", 1)[0]
value_text = pieces[0].split("=", 1)[1] if "=" in pieces[0] else (pieces[1] if len(pieces) > 1 else None)
if key != control_name or value_text is None:
    continue
```

`v4l2-ctl -C <kontrol>` outputter formatet `"<kontrolnavn>: <værdi>"` (kolon+mellemrum), **ikke**
`"<kontrolnavn>=<værdi>"`. Fx: `exposure_auto: 1`.

Når linjen splittes på whitespace bliver `pieces[0]` lig `"exposure_auto:"` — **med kolon**. Da der
ikke er noget `"="` i strengen, sættes `key = "exposure_auto:"` uændret. Denne værdi vil **aldrig**
være lig `control_name` (`"exposure_auto"`, uden kolon), så betingelsen `key != control_name` er
altid sand, og funktionen fortsætter forbi alle linjer og rammer til sidst `return None`
([L429](hardware/camera.py#L429)).

**Konsekvens:** `_read_v4l2_control()` returnerer **altid `None`** på Linux, uanset hvad driveren
reelt rapporterer. `get_auto_exposure()`, `get_exposure()` og `get_gain()` falder derfor altid
tilbage til OpenCV's `CAP_PROP_*`-læsning i stedet for den tiltænkte direkte V4L2-læsning — se
fund #3 for hvorfor det er problematisk.

Denne fejl er uafhængig af fund #1: selv hvis `v4l2-ctl` er installeret og virker perfekt, vil
funktionen aldrig genkende dens output korrekt.

### Fund #3 (sandsynlig, afhænger af OpenCV-version): Uens værdikonvention i fallback-læsning

Når `_read_v4l2_control()` returnerer `None` (jf. fund #2), falder `get_auto_exposure()` tilbage
til:
```python
value = self._property("CAP_PROP_AUTO_EXPOSURE")
return self._interpret_auto_exposure_value(value)
```

`_interpret_auto_exposure_value()` ([camera.py L446-462](hardware/camera.py#L446-L462)) forsøger at
tolke **to forskellige konventioner** i samme funktion:
- DirectShow-stil (Windows): `0.25` = manuel, `0.75` = auto
- Rå V4L2-menu-heltal (Linux): `1` = manuel, `≥2` = auto

OpenCV's V4L2-backend er historisk **inkonsistent på tværs af versioner** i, om
`CAP_PROP_AUTO_EXPOSURE` returnerer den rå V4L2-menuværdi (0-3) eller en normaliseret float. Hvis
den installerede `opencv-python`-version på Pi'en afviger fra den antagelse, kan
`_interpret_auto_exposure_value()` **fejltolke tilstanden** — fx rapportere "auto" når kameraet
reelt står i manuel tilstand, hvilket ville få GUI'en (efter vores tidligere rettelse, der nu
stoler på denne returværdi) til korrekt at "opdage" en tilstand, der reelt ikke stemmer med
driveren.

**Diagnosticeringskommando:**
```bash
python3 -c "import cv2; print(cv2.__version__)"
v4l2-ctl -d /dev/video0 --list-ctrls | grep -i exposure
```

### Fund #4 (mindre sandsynlig, men til stede): Ingen retry/delay og intet flertydigt kontrolnavn-fallback ved skrivning på Linux

Windows/generisk-stien i `set_auto_exposure()` prøver **flere kandidatværdier** og venter 30 ms
mellem hvert forsøg, før den læser tilbage og verificerer
([camera.py L502-514](hardware/camera.py#L502-L514)). Linux-stien
([camera.py L478-495](hardware/camera.py#L478-L495)) sender derimod **kun ét enkelt**
`v4l2-ctl -c exposure_auto=<1|3>`-kald, uden ventetid og uden fallback til alternative
kontrolnavne. Nogle UVC-drivere eksponerer kontrollen under et andet navn (fx `auto_exposure`
i stedet for `exposure_auto`), afhængigt af kernel-/driverversion. Hvis kontrolnavnet er forkert
for det specifikke kamera, fejler `v4l2-ctl` med en ukendt-kontrol-fejl, som (jf. fund #1) bliver
tavst ignoreret.

**Diagnosticeringskommando:**
```bash
v4l2-ctl -d /dev/video0 --list-ctrls
```
Bekræft at kontrollen faktisk hedder `exposure_auto` (ikke fx `auto_exposure` eller noget andet)
på netop dette kamera.

### Fund #5 (strukturel svaghed, ikke roden til problemet men bør rettes): `supports_auto_exposure()` er ubetinget `True` på Linux

```python
def supports_auto_exposure(self) -> bool:
    if sys.platform.startswith("linux"):
        return True
    return self._property("CAP_PROP_AUTO_EXPOSURE") is not None
```

På Linux antages det altid, at kameraet understøtter auto-eksponerings-styring, uden nogen reel
kontrol af, om kontrollen findes på det tilsluttede kamera. Det betyder, at checkbox/spinbox i
GUI'en fremstår "understøttet" og aktiv, selv på kameraer der reelt ikke har denne kontrol —
hvilket kan maskere et hardware-/driverbegrænsning som et softwareproblem.

## 5. Anbefalet rækkefølge for verifikation på Pi'en

1. `which v4l2-ctl` — bekræft/afkræft fund #1.
2. `v4l2-ctl -d /dev/video0 --list-ctrls` — bekræft eksakt kontrolnavn og understøttede værdier (fund #4, #5).
3. Kør manuelt: `v4l2-ctl -d /dev/video0 -c exposure_auto=1` og verificér direkte med
   `v4l2-ctl -d /dev/video0 -C exposure_auto` at værdien reelt ændrer sig — dette isolerer om
   problemet ligger i driveren/kameraet eller i Python-koden.
4. Ret parsing-fejlen i `_read_v4l2_control()` (fund #2) — nem, lavrisiko rettelse.
5. Overvej at erstatte `subprocess`-kald til `v4l2-ctl` med direkte V4L2-ioctl-kald (fx via
   biblioteket `v4l2py` eller `python-v4l2`), så løsningen ikke er afhængig af en ekstern binær der
   skal installeres separat og ikke er versionsstyret sammen med projektet.

## 6. Opsummering til rapporten

Den primære, mest sandsynlige årsag er en kombination af **manglende ekstern afhængighed**
(`v4l-utils`, fund #1) og en **parsing-fejl** i tilbagelæsningen af V4L2-kontroller (fund #2), som
sammen gør, at softwaren enten (a) aldrig reelt sender ændringen til kameraet, eller (b) sender den
korrekt, men aldrig kan bekræfte det over for resten af systemet, fordi tilbagelæsningen er
strukturelt i stykker. Begge er reproducerbare og verificerbare uden gæt, via kommandoerne i
afsnit 5.
