import { defineCustomElement } from 'vue'
import Navbar from './components/DevdocsNavbar.vue'

// convert into custom element constructor
const DevdocsNavbar = defineCustomElement(Navbar, { shadowRoot: false })

// register
customElements.define('devdocs-navbar', DevdocsNavbar)
