from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, Text, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


LILAC = '#ceb1ff'
TORQUOISE = '#1bc5e0'


class WitchHazelStyle(Style):
    """
    This style is a witchy theme based on sailorhg's fairyfloss
    https://github.com/sailorhg/fairyfloss/blob/gh-pages/fairyfloss.tmTheme
    """

    background_color = "#433e56"
    highlight_color = "#716799"

    styles = {
        # No corresponding class for the following:
        Text:                      "#F8F8F2",  # class:  ''
        Whitespace:                "#A8757B",        # class: 'w'
        Error:                     "#960050 bg:#1e0010",  # class: 'err'
        Other:                     "",        # class 'x'

        Comment:                   "#b0bec5",  # class: 'c'
        Comment.Multiline:         "",        # class: 'cm'
        Comment.Preproc:           "",        # class: 'cp'
        Comment.Single:            "",        # class: 'c1'
        Comment.Special:           "",        # class: 'cs'

        Keyword:                   "#C2FFDF",  # class: 'k' italic?
        Keyword.Constant:          "",        # class: 'kc'
        Keyword.Declaration:       "",        # class: 'kd' italic?
        Keyword.Namespace:         "#FFB8D1",  # class: 'kn'
        Keyword.Pseudo:            "",        # class: 'kp'
        Keyword.Reserved:          "",        # class: 'kr'
        Keyword.Type:              "",        # class: 'kt' italic?

        Operator:                  "#FFB8D1",  # class: 'o'
        Operator.Word:             "",        # class: 'ow' - like keywords

        Punctuation:               "#F8F8F2",  # class: 'p'

        Name:                      "#F8F8F2",  # class: 'n'
        Name.Attribute:            LILAC,  # class: 'na'
        Name.Builtin:              "",        # class: 'nb'
        Name.Builtin.Pseudo:       "#80cbc4",        # class: 'bp'
        Name.Class:                LILAC,  # class: 'nc' italic underline?
        Name.Constant:             "#C5A3FF",  # class: 'no'
        Name.Decorator:            LILAC,  # class: 'nd' underline?
        Name.Entity:               "",        # class: 'ni'
        Name.Exception:            LILAC,  # class: 'ne' underline?
        Name.Function:             LILAC,  # class: 'nf'
        Name.Property:             "#F8F8F2",        # class: 'py'
        Name.Label:                "",        # class: 'nl'
        Name.Namespace:            "",        # class: 'nn' - to be revised
        Name.Other:                "",  # class: 'nx'
        Name.Tag:                  "#FFB8D1",  # class: 'nt' - like a keyword
        Name.Variable:             "#F8F8F2",        # class: 'nv' - to be revised
        Name.Variable.Class:       "",        # class: 'vc' - to be revised
        Name.Variable.Global:      "",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "",        # class: 'vi' - to be revised

        Number:                    "#C5A3FF",  # class: 'm'
        Number.Float:              "",        # class: 'mf'
        Number.Hex:                "",        # class: 'mh'
        Number.Integer:            "",        # class: 'mi'
        Number.Integer.Long:       "",        # class: 'il'
        Number.Oct:                "",        # class: 'mo'

        Literal:                   "#ae81ff",  # class: 'l'
        Literal.Date:              "#e6db74",  # class: 'ld'

        String:                    TORQUOISE,  # class: 's'
        String.Backtick:           "",        # class: 'sb'
        String.Char:               "",        # class: 'sc'
        String.Doc:                "",        # class: 'sd' - like a comment
        String.Double:             "",        # class: 's2'
        String.Escape:             "",  # class: 'se'
        String.Heredoc:            "",        # class: 'sh'
        String.Interpol:           "",        # class: 'si'
        String.Other:              "",        # class: 'sx'
        String.Regex:              "",        # class: 'sr'
        String.Single:             "",        # class: 's1'
        String.Symbol:             "",        # class: 'ss'

        Generic:                   "",        # class: 'g'
        Generic.Deleted:           "#f92672",  # class: 'gd',
        Generic.Emph:              "italic",  # class: 'ge'
        Generic.Error:             "",        # class: 'gr'
        Generic.Heading:           "",        # class: 'gh'
        Generic.Inserted:          "#a6e22e",  # class: 'gi'
        Generic.Output:            "",        # class: 'go'
        Generic.Prompt:            "",        # class: 'gp'
        Generic.Strong:            "bold",    # class: 'gs'
        Generic.Subheading:        "#75715e",  # class: 'gu'
        Generic.Traceback:         "",        # class: 'gt'
    }
