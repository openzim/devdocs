<script setup lang="ts">
const props = defineProps<{
  // Current page.
  current: string
  // Prefix to prepend to links.
  prefix: string
  // Listing
  listingSrc: string
}>()

import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

// JSONPath indicating the root page.
const ROOT_PAGE_ID = ".landingHref"

// A page in the navbar.
interface PageEntry {
  // Display name of the page.
  name: string
  // Link to the content.
  href: string
  // Whether the page is highlighted in the navbar.
  isSelected: boolean
  // Generated ID for the page (JSONPath)
  id: string
}

// A section in the navbar.
interface SectionEntry {
  // Display name of the section.
  name: string
  // Whether the section is opened in the navbar.
  isOpen: boolean
  // Pages of content organized under this section.
  children: PageEntry[]
  // Generated ID of the section (JSONPath).
  id: string
}

interface Document {
  // Display name of the document in the navbar.
  name: string
  // Root page link for the navbar.
  landingHref: string
  // Whether the root page is selected.
  isSelected: boolean
  // Link to the OSS licenses for the content.
  licenseHref: string
  // Version number of the document to display.
  version: string
  // Sections which organize the document's content.
  children: SectionEntry[]
}

// Is there an error rendering?
const error = ref('')
// Navigation to display.
const navigation = ref<Document>({
  name: 'Loading...',
  landingHref: '#',
  isSelected: false,
  licenseHref: '',
  version: '',
  children: []
})

// Currently selected page which may differ from the original if the user clicks a link
// in the sidebar.
const selectedPageId = ref("")

// Map of section ID to open state if opened/closed by the user.
const sectionOpenStates = ref(new Map<string, boolean>())

// Make a link relative using props.prefix.
function makeRelative(link: string): string {
  return props.prefix + link
}

// Navigation state to be rendered.
const displayNavigation = computed(() => {
  const output: Document = {
    name: navigation.value.name,
    version: navigation.value.version,
    landingHref: makeRelative(navigation.value.landingHref),
    licenseHref: makeRelative(navigation.value.licenseHref),
    isSelected: ROOT_PAGE_ID === selectedPageId.value,
    children: []
  }

  for (var section of navigation.value.children) {
    const sectionEntry: SectionEntry = {
      name: section.name,
      isOpen: false,
      children: [],
      id: section.id,
    }

    var hasSelectedChild = false;
    for (var page of section.children) {
      const pageEntry: PageEntry = {
        name: page.name,
        href: makeRelative(page.href),
        isSelected: page.id === selectedPageId.value,
        id: page.id,
      }

      hasSelectedChild = hasSelectedChild || pageEntry.isSelected;

      sectionEntry.children.push(pageEntry)
    }

    // Sections take on the last state a person set on them.
    // By default, they're open if one of their children is selected.
    sectionEntry.isOpen = sectionOpenStates.value.get(sectionEntry.id) ?? hasSelectedChild

    output.children.push(sectionEntry)
  }

  return output
})

// Load the navigation data when the component is rendered.
onMounted(() => {
  axios.get(props.listingSrc, {
        headers: {
          Accept: 'application/json',
        },
      },
  ).then(response => {
    if (response.status != 200) {
      error.value = `Loading navigation from ${props.listingSrc} failed status: ${response.status}`
    } else {
      var navbarData: Document = response.data

      var hrefMapping = new Map();
      hrefMapping.set(navbarData.landingHref, ROOT_PAGE_ID);

      // Set up unique IDs for each navbar entry so they can be highlighted
      // individually.
      for (const [sectionNum, section] of navbarData.children.entries()) {
        section.id = `.children[${sectionNum}]`

        for (const [pageNum, page] of section.children.entries()) {
          page.id = `${section.id}.children[${pageNum}]`

          if (! hrefMapping.has(page.href)) {
            hrefMapping.set(page.href, page.id)
          }
        }
      }

      // Find the currently highlighted page.
      const currentPageWithHash = props.current + window.location.hash
      if (hrefMapping.has(currentPageWithHash)) {
        // Highlight a link to the selected heading if one exists.
        selectedPageId.value = hrefMapping.get(currentPageWithHash)
      } else {
        // Highlight the parent page if one exists, otherwise nothing.
        selectedPageId.value = hrefMapping.get(props.current) ?? ""
      }

      navigation.value = navbarData
    }
  }).catch(error => {
    error.value = `Loading navigation from ${props.listingSrc} failed with error: ${error}`
  })
})

// Updates the current page to bet the selected one.
function setCurrentPage(pageId: string, path: string, event: Event) {
  selectedPageId.value = pageId

  // Handle the special case where multiple links point to the same document.
  // We want the user to be able to get the right highlighting when they click
  // but not refresh the page which would highlight the wrong item.
  const currentPageRelative = makeRelative(props.current);
  if (path === currentPageRelative) {
    event.preventDefault()
  }
}

// Switches the open state of the given section.
function toggleSection(sectionId: string, isOpen: boolean) {
  sectionOpenStates.value.set(sectionId, !isOpen)
}
</script>

<template>
  <section class="_sidebar">
    <div v-if="error" role="navigation" class="_list">
      <div class="_error">{{ error }}</div>
    </div>
    <div v-else role="navigation" class="_list">
      <a
        :href="displayNavigation.landingHref"
        :class="[{ active: displayNavigation.isSelected }, '_list-item', '_list-dir']"
      >
        <span class="_list-count">{{ displayNavigation.version }}</span>
        <span class="_list-text">{{ displayNavigation.name }}</span>
      </a>

      <div
        v-for="section of displayNavigation.children"
        class="_list _list-dir"
        v-bind:key="section.name"
      >
        <a
          :class="['_list-item', '_list-dir', { open: section.isOpen }]"
          @click="toggleSection(section.id, section.isOpen)"
        >
          <svg class="_list-arrow" v-if="section.children"><use xlink:href="#icon-dir"></use></svg>
          <span class="_list-count">{{ section.children.length }}</span>
          <span class="_list-text">{{ section.name }}</span>
        </a>

        <div class="_list _list-sub" v-if="section.isOpen">
          <a
            v-for="page in section.children"
            :key="page.name"
            :href="page.href"
            :class="[{ active: page.isSelected }, '_list-item', '_list-hover']"
            @click="setCurrentPage(page.id, page.href, $event)"
            >{{ page.name }}</a
          >
        </div>
      </div>

      <a :href="displayNavigation.licenseHref" class="_list-item _list-hover">
        <span class="_list-text">Open Source Licenses</span>
      </a>
    </div>
  </section>

  <!--
    Right facing triangle icon taken from:
    https://github.com/freeCodeCamp/devdocs/blob/eabf2f38277663cd6c9b3bfbd6ee52238b12c731/views/app.erb#L55
  -->
  <svg
    style="display: none"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <defs>
      <symbol id="icon-dir" viewBox="0 0 20 20">
        <path
          d="M15 10c0 .3-.305.515-.305.515l-8.56 5.303c-.625.41-1.135.106-1.135-.67V4.853c0-.777.51-1.078 1.135-.67l8.56 5.305S15 9.702 15 10z"
        ></path>
      </symbol>
    </defs>
  </svg>
</template>

<style>
/* Style fixes for DevDocs CSS. */
._sidebar {
  padding-top: 0;
}

._list-dir {
  padding-left: 0 !important;
}

._list-item:before, ._docs-name:before, ._path-item:first-child:before {
  background-image: none;
}
</style>
