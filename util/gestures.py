from time import sleep

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction

from util.parsing import parse_cell_label


def tap(driver, x, y):
    driver.execute_script('mobile: tap', {'x': x, 'y': y})


def swipe(driver, from_x, from_y, to_x, to_y, duration=1.0):
    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    actions.w3c_actions.pointer_action.move_to_location(from_x, from_y)
    actions.w3c_actions.pointer_action.pointer_down()
    actions.w3c_actions.pointer_action.pause(duration)
    actions.w3c_actions.pointer_action.move_to_location(to_x, to_y)
    actions.w3c_actions.pointer_action.release()
    actions.perform()


def back_swipe(driver, window_height):
    '''Quick left-edge swipe to trigger iOS back navigation.'''
    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    actions.w3c_actions.pointer_action.move_to_location(5, window_height // 2)
    actions.w3c_actions.pointer_action.pointer_down()
    actions.w3c_actions.pointer_action.move_to_location(200, window_height // 2)
    actions.w3c_actions.pointer_action.release()
    actions.perform()


def long_press(driver, x, y, duration=1.5):
    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    actions.w3c_actions.pointer_action.move_to_location(x, y)
    actions.w3c_actions.pointer_action.pointer_down()
    actions.w3c_actions.pointer_action.pause(duration)
    actions.w3c_actions.pointer_action.release()
    actions.perform()


def long_press_copy_link(driver, x, y, window_height):
    '''Long-press at (x, y) and tap "Copy Link" from the context menu.
    Returns (link_text, None). Dismisses via top of screen if no Copy Link.'''
    print("  Long-pressing at {}, {}".format(x, y))
    long_press(driver, x, y, duration=1.5)
    sleep(0.1)

    try:
        copy_el = driver.find_element(AppiumBy.ACCESSIBILITY_ID, 'Copy Link')
        cx = copy_el.location['x'] + copy_el.size['width'] // 2
        cy = copy_el.location['y'] + copy_el.size['height'] // 2
        tap(driver, cx, cy)
        sleep(0.5)
        return driver.get_clipboard_text(), None
    except Exception:
        print("  No 'Copy Link' found, dismissing")
        tap(driver, 200, 30)  # status bar — safely above all story cards
        sleep(1.5)
        return None, None


def get_article_headline(driver, x, y, window_height):
    '''Tap a story card at (x, y), extract the publication and headline from
    the article view, then tap the Back button.

    Returns (headline, publication) — either or both may be '' on failure.

    Primary source: the article ScrollView whose name attribute is
    "Publication, Headline". This is the most reliable element and also
    provides the publication name, which is useful for sections (e.g.
    trending) where the cell label does not include a publication.

    Fallback (headline only): XCUIElementTypeOther elements with
    traits="Header", skipping short category labels like "World news".
    '''
    tap(driver, x, y)
    sleep(3)

    article_headline = ''
    article_publication = ''
    try:
        # The article ScrollView's name attribute is "Publication, Headline".
        scroll_els = driver.find_elements(
            AppiumBy.XPATH, '//XCUIElementTypeScrollView[contains(@name, ",")]'
        )
        for el in scroll_els:
            name = (el.get_attribute('name') or '').strip()
            if len(name) > 20:
                pub, headline, _ = parse_cell_label(name)
                if headline:
                    article_headline = headline
                    article_publication = pub
                    break
    except Exception:
        pass

    if not article_headline:
        try:
            # Fallback: traits="Header" elements, skipping short category labels
            # (e.g. "World news", "Technology") which appear before the headline.
            els = driver.find_elements(AppiumBy.XPATH, '//XCUIElementTypeOther[@traits="Header"]')
            for el in els:
                val = (el.get_attribute('value') or '').strip()
                if len(val) > 20:
                    article_headline = val
                    break
        except Exception:
            pass

    try:
        back_btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, 'BackButton')
        tap(driver, back_btn.location['x'] + back_btn.size['width'] // 2,
            back_btn.location['y'] + back_btn.size['height'] // 2)
    except Exception:
        back_swipe(driver, window_height)
    sleep(2)

    return article_headline, article_publication
