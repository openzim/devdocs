import Prism from 'prismjs'

// Devdocs vendors all their Prism dependencies.
// The list of supported languages is in:
// https://github.com/freeCodeCamp/devdocs/blob/main/assets/javascripts/vendor/prism.js
// The list below is sorted in the same order as the URL with exceptions noted.
import 'prismjs/components/prism-markup'
import 'prismjs/components/prism-css'
import 'prismjs/components/prism-clike'
import 'prismjs/components/prism-javascript'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-c'
import 'prismjs/components/prism-cpp'
import 'prismjs/components/prism-cmake'
import 'prismjs/components/prism-coffeescript'
import 'prismjs/components/prism-d'
import 'prismjs/components/prism-dart'
import 'prismjs/components/prism-diff'
import 'prismjs/components/prism-elixir'
import 'prismjs/components/prism-erlang'
import 'prismjs/components/prism-go'
import 'prismjs/components/prism-groovy'
import 'prismjs/components/prism-java'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-julia'
import 'prismjs/components/prism-kotlin'
import 'prismjs/components/prism-latex'
import 'prismjs/components/prism-lua'
import 'prismjs/components/prism-markdown'
import 'prismjs/components/prism-markup-templating'
import 'prismjs/components/prism-django'  // Must come after markup-templating
import 'prismjs/components/prism-matlab'
import 'prismjs/components/prism-nginx'
import 'prismjs/components/prism-nim'
import 'prismjs/components/prism-nix'
import 'prismjs/components/prism-ocaml'
import 'prismjs/components/prism-perl'
import 'prismjs/components/prism-php'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-qml'
import 'prismjs/components/prism-r'
import 'prismjs/components/prism-jsx'
import 'prismjs/components/prism-ruby'
import 'prismjs/components/prism-crystal' // Must come after ruby
import 'prismjs/components/prism-rust'
import 'prismjs/components/prism-scss'
import 'prismjs/components/prism-scala'
import 'prismjs/components/prism-shell-session'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-typescript'
import 'prismjs/components/prism-yaml'
import 'prismjs/components/prism-zig'

function highlightSyntax() {
    for (const element of document.querySelectorAll("pre[data-language]")) {

        // Devdocs adds the attribute data-language, but Prism uses classes
        // to decide what to highlight.
        const language = element.getAttribute("data-language")
        element.classList.add(`language-${language}`)

        // Highlight the element.
        Prism.highlightElement(element)
    }
}

// Do syntax highlighting on page load.
document.addEventListener("DOMContentLoaded", highlightSyntax)
