import re
import datetime


def parse_cell_label(label):
    '''Parse a cell label into (publication, headline, author).

    Handles these formats:
      "Publication, Headline, time ago[, Author]"
      "BREAKING, Publication, Headline, time ago[, Author]"
      "Publication, Apple News Plus, Headline, time ago[, Author]"
      "Headline with commas, Apple News Plus, time ago[, Author]"  (trending, no publication)
      "Blurb text..., Play Now, ..."  (audio cell — no publication)

    The key disambiguation: if the text before ", Apple News Plus, " contains
    a comma, it is a multi-part headline with no publication. If it has no
    comma, it is a publication name.
    '''
    if not label:
        return '', '', ''

    # Audio cells: the blurb is the headline, publisher is Apple News Today
    for audio_marker in (', Play Now', ', Listen to the day'):
        if audio_marker in label:
            headline = label.split(audio_marker, 1)[0].strip()
            return 'Apple News Today', headline, ''

    plus_marker = ', Apple News Plus, '
    if plus_marker in label:
        before_plus, after_plus = label.split(plus_marker, 1)
        if ',' not in before_plus:
            # "Publication, Apple News Plus, Headline, time, Author"
            publication = before_plus
            rest = after_plus
        else:
            # "Headline with commas, Apple News Plus, time, Author" — no publication
            publication = ''
            headline = before_plus
            time_match = re.search(r'^\d+\s+(?:hour|minute|day|week|month)s?\s+ago', after_plus)
            author = after_plus[time_match.end():].lstrip(', ').strip() if time_match else ''
            return publication, headline, author
    else:
        parts = label.split(', ', 1)
        if len(parts) < 2:
            return label, '', ''
        publication = parts[0]
        rest = parts[1]

        # Breaking news prefix: "BREAKING, ActualPublication, Headline..."
        if publication.strip() == 'BREAKING':
            sub = rest.split(', ', 1)
            if len(sub) >= 2:
                publication, rest = sub[0], sub[1]
            else:
                publication = ''

    time_match = re.search(r',\s*\d+\s+(?:hour|minute|day|week|month)s?\s+ago', rest)
    if time_match:
        headline = rest[:time_match.start()].strip()
        author = rest[time_match.end():].lstrip(', ').strip()
    else:
        headline = rest
        author = ''
    return publication, headline, author


def parse_pub_date(label):
    '''Estimate publication datetime from "X hours/minutes/days ago" in a cell label.'''
    m = re.search(r'(\d+)\s+(minute|hour|day|week|month)s?\s+ago', label)
    if not m:
        return ''
    n, unit = int(m.group(1)), m.group(2)
    delta = {
        'minute': datetime.timedelta(minutes=n),
        'hour':   datetime.timedelta(hours=n),
        'day':    datetime.timedelta(days=n),
        'week':   datetime.timedelta(weeks=n),
        'month':  datetime.timedelta(days=n * 30),
    }.get(unit, datetime.timedelta())
    return (datetime.datetime.now() - delta).strftime('%Y-%m-%d %H:%M:%S')
