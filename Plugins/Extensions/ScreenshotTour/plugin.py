from os import makedirs, system
from os.path import join
from traceback import print_exc

from enigma import eTimer

from Plugins.Plugin import PluginDescriptor
from Screens.Menu import Menu, findMenu
from Screens.Setup import Setup

try:
    # Only present since the Components.NetworkManager rewrite (added 2026-08-16).
    # The test image can be older, so this must not break the whole plugin import.
    from Components.NetworkManager import networkManager
    from Screens.NetworkSetup import NetworkAdapterSetup
except ImportError:
    networkManager = None
    NetworkAdapterSetup = None

SHOTS_DIR = "/tmp/shots"

# Only setup.xml keys that a plain Setup(session, setup=key) can render.
# Keys whose items reference "self.xxx" (NetworkAdapter, RecordTimer, DNS, ...)
# need a dedicated Screen subclass that builds those attributes first.
SETUP_KEYS = [
    "Usage", "Audio", "UserInterface", "Skin", "Subtitle", "VolumeAdjust",
    "AutoLanguage", "ChannelSelection", "Display", "EPG", "EPGEnhanced",
    "EPGGraphical", "EPGInfobar", "EPGInfobarGraphical", "EPGMulti", "EPGSingle",
    "EPGVertical", "HardDisk", "HDMIRecord", "InputDeviceSetup", "Keyboard",
    "LEDs", "Locale", "Logs", "MovieSelection", "OSD3DCalibration",
    "OSDCalibration", "Password", "Picon", "Playback", "PluginBrowser",
    "Recording", "RemoteButton", "SoftwareManager", "SpecialFeatures", "Time",
    "Timeshift", "Cardserver", "CCcamLineEdit", "CCcamProfile", "CiSelection",
    "OSCamInfoSetup", "SoftCSA", "Softcam", "StreamRelay", "RFModulator",
    "Satellite", "Tuner", "HDMICEC", "NetworkZeroTier", "FlashExpander",
]

MENU_KEYS = [
    "mainmenu", "information", "timermenu", "setup", "video_menu",
    "audio_menu", "rec", "system", "epg", "scan", "cam", "software_manager",
    "network", "extended", "shutdown",
]

timer = None  # keeps the eTimer instance alive between callbacks


def Plugins(**kwargs):
    return [PluginDescriptor(name="ScreenshotTour", description="Take screenshots of setup and menu screens for CI", where=PluginDescriptor.WHERE_SESSIONSTART, fnc=autostart)]


def buildScreens():
    screens = [(f"setup_{key}", Setup, {"setup": key}) for key in SETUP_KEYS]
    if networkManager is not None:
        adapter = next(iter(networkManager.adapters.values()), None)
        if adapter is not None:
            screens.append(("setup_networkadapter", NetworkAdapterSetup, {"adapter": adapter}))
    for key in MENU_KEYS:
        menu = findMenu(key)
        if menu is not None:
            screens.append((f"menu_{key}", Menu, {"parentMenu": menu}))
    return screens


def autostart(reason, session=None, **kwargs):
    global timer
    if reason == 0 and session is not None:
        makedirs(SHOTS_DIR, exist_ok=True)

        def startTour():
            runTour(session, buildScreens())

        timer = eTimer()
        timer.callback.append(startTour)
        timer.start(5000, True)


def runTour(session, remaining):
    global timer
    if not remaining:
        open("/tmp/screenshot_tour_done", "w").close()
        return
    name, cls, kwargs = remaining.pop(0)
    try:
        scr = session.openWithCallback(lambda *closeArgs: runTour(session, remaining), cls, **kwargs)
    except Exception:
        print(f"[ScreenshotTour] Error: Failed to open screen '{name}'.")
        print_exc()
        runTour(session, remaining)
        return

    def afterRender():
        system(f"import -window root {join(SHOTS_DIR, name)}.png")
        scr.close()

    timer = eTimer()
    timer.callback.append(afterRender)
    timer.start(1500, True)
