import os
import sys
import re

sys_encoding = sys.getfilesystemencoding()
addon_path = os.path.dirname(__file__)

def decloze_util(text):
    cloze_anki_regex = re.compile(r'\{\{c[0-9]+::([^(::)(\}\})]*)(?:::[^(?:\}\})]*)?\}\}')
    cloze_overlapper_regex = re.compile(r'\[\[oc[0-9]+::([^(::)(\]\])]*)(?:::[^(?:\]\])]*)?\]\]')

    result = cloze_overlapper_regex.sub(
        r'\1',
        cloze_anki_regex.sub(r'\1', text),
    )

    return result


def stdlib_util():
    print(
'''
ark() {

    if [[ "$#" -eq 0 ]]; then
        set ''
    fi

    if [[ "$1" =~ ^(-.*|paths|stats|pagerefs|revpagerefs|headings|verify|query|match|browse|add|decloze|stdlib)$ ]]; then
        command exec ark "$@"

    else
        arr="$(command ark paths "$1")"
        local entry
        exitstatus=$?
         [[ ! $exitstatus == '0' ]] && return $exitstatus
        read -a entry <<< "${arr[@]}"

        if [[ -d ${entry} ]]; then
            exec cd "${entry}"

        elif [[ -f ${entry} ]]; then
            exec $EDITOR "${entry}"

        elif [[ "${entry}" =~ ^(.*):(.*): ]]; then
            exec $EDITOR "${BASH_REMATCH[1]}" +${BASH_REMATCH[2]} -c 'normal! zz'
        fi
    fi
}

alias hasq="awk '{ if(\$2 != 0) { print \$0 } }'"
alias noq="awk '{ if(\$2 == 0) { print \$0 } }'"

alias noma="awk '{ if(\$2 != \$3 ) { print \$0 } }'"
alias miss="awk '{ if(\$3 != 1) { print \$0 } }'"

# for use with ark headings (getting the document title)
alias dt="grep '^[^=]*$'"
'''
)
