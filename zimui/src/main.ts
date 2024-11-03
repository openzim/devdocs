import { defineCustomElement } from 'vue'
import Navbar from './components/DevdocsNavbar.vue'
import './highlighter'

// Convert the navbar into a custom element. We're using this rather than
// the shorthand .ce.vue naming because we need to disable shadowRoot
// so the DevDocs CSS will work on the navigation entries.
const DevdocsNavbar = defineCustomElement(Navbar, { shadowRoot: false })
customElements.define('devdocs-navbar', DevdocsNavbar)
