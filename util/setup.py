import os
import re
import json
import subprocess
from shutil import rmtree
from glob import glob


# Path where Appium stores the compiled WDA xctest bundle.
_WDA_DERIVED_DATA_PATTERN = os.path.expanduser(
    '~/Library/Developer/Xcode/DerivedData/WebDriverAgent-*'
)

# Appium embeds the target SDK in the xctestrun filename, e.g.:
#   WebDriverAgentRunner_iphonesimulator26.2-arm64.xctestrun
# We parse this to detect iOS SDK version mismatches before connecting.
_XCTESTRUN_GLOB = os.path.join(_WDA_DERIVED_DATA_PATTERN, 'Build/Products/*.xctestrun')


def wda_needs_rebuild(target_udid):
    '''Return True if WDA must be rebuilt before the next Appium session.

    Detection logic:
      1. Look for a compiled WDA xctestrun file under Xcode DerivedData.
         If none exists, WDA has never been built → needs build.
      2. Ask the simulator what iOS version it is running (xcrun simctl).
      3. Compare that version to the SDK version embedded in the xctestrun
         filename (e.g. "iphonesimulator26.2" → "26.2").
         If they differ, the old bundle will crash when Appium tries to
         start a session on the newer runtime → needs rebuild.

    When this function returns True, callers should:
      - delete DerivedData via clear_wda_derived_data()
      - set the Appium capability usePrebuiltWDA=False

    On any error (simctl unavailable, unexpected filename format, etc.)
    returns False so as not to trigger an unnecessary rebuild.
    '''
    xctestrun_files = glob(_XCTESTRUN_GLOB)
    if not xctestrun_files:
        return True  # no build at all

    # Ask the simulator for its current runtime version.
    try:
        result = subprocess.run(
            ['xcrun', 'simctl', 'list', 'devices', '--json'],
            capture_output=True, text=True, check=True,
        )
        devices_json = json.loads(result.stdout)
    except Exception as e:
        print("wda_needs_rebuild: could not query simctl ({}) — skipping rebuild check".format(e))
        return False

    # Find the runtime key for our target UDID.
    # Runtime keys look like "com.apple.CoreSimulator.SimRuntime.iOS-26-3".
    sim_version = None
    for runtime_key, device_list in devices_json.get('devices', {}).items():
        for device in device_list:
            if device.get('udid') == target_udid:
                m = re.search(r'iOS-(\d+)-(\d+)', runtime_key)
                if m:
                    sim_version = '{}.{}'.format(m.group(1), m.group(2))
                break
        if sim_version:
            break

    if not sim_version:
        print("wda_needs_rebuild: could not find simulator {} in simctl output — skipping rebuild check".format(target_udid))
        return False

    # Check whether any existing xctestrun was compiled for the current SDK.
    # Filename format: WebDriverAgentRunner_iphonesimulator<SDK>-<arch>.xctestrun
    for path in xctestrun_files:
        basename = os.path.basename(path)
        if 'iphonesimulator{}'.format(sim_version) in basename:
            return False  # existing build matches current simulator version

    # All found xctestrun files target a different SDK.
    built_versions = [os.path.basename(p) for p in xctestrun_files]
    print("wda_needs_rebuild: simulator is iOS {} but WDA was built for: {}".format(
        sim_version, built_versions))
    return True


def clear_wda_derived_data():
    '''Delete all WDA DerivedData directories so Appium rebuilds from source.

    Safe to call even if no DerivedData exists (glob returns empty list).
    Appium will rebuild WDA automatically on the next session when
    usePrebuiltWDA=False is set in the capabilities.
    '''
    for path in glob(_WDA_DERIVED_DATA_PATTERN):
        try:
            rmtree(path)
            print("clear_wda_derived_data: removed {}".format(path))
        except Exception as e:
            print("clear_wda_derived_data: could not remove {} ({})".format(path, e))


def wipe_app_data_folder(path):
    for f in os.listdir(path):
        full = '{}/{}'.format(path, f)
        if os.path.isfile(full):
            os.remove(full)
        else:
            rmtree(full)
