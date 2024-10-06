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

interface PageEntry {
  name: string
  href: string
  isSelected: boolean
}

interface SectionEntry {
  name: string
  isOpen: boolean
  children: PageEntry[]
}

interface Document {
  name: string
  href: string
  isSelected: boolean
  licenseHref: string
  version: string
  children: SectionEntry[]
}

// Is the index loading?
const loading = ref(true)
// Is there an error rendering?
const error = ref('')
// Navigation to display.
const navigation = ref<Document>({
  name: 'Loading...',
  href: '#',
  isSelected: false,
  licenseHref: '#',
  version: '',
  children: []
})
// Currently selected page which may differ from the original if the user clicks a link
// in the sidebar.
const currentPage = ref(props.current)
// Map of section name to open state.
const sectionOpenStates = ref(new Map<string, boolean>())

/* Make a link relative using props.prefix. */
function makeRelative(link: string): string {
  return props.prefix + link
}

const allHrefs = computed(() => {
  const hrefList = navigation.value.children
    .map((section) => section.children)
    .flat()
    .map((page) => page.href)

  // Push in the root href (should always be /index.html)
  hrefList.push(navigation.value.href)

  return new Set(hrefList)
})

/* Get the href that most closely represents the current page so it can be highlighted. */
const highlightedHref = computed(() => {
  const currentPageWithHash = currentPage.value + window.location.hash

  if (allHrefs.value.has(currentPageWithHash)) {
    return currentPageWithHash
  }

  return currentPage.value
})

const displayNavigation = computed(() => {
  const output: Document = {
    name: navigation.value.name,
    version: navigation.value.version,
    href: makeRelative(navigation.value.href),
    licenseHref: makeRelative(navigation.value.licenseHref),
    isSelected: navigation.value.href === highlightedHref.value,
    children: []
  }

  for (var section of navigation.value.children) {
    const sectionEntry: SectionEntry = {
      name: section.name,
      children: [],
      isOpen: false
    }

    for (var page of section.children) {
      const pageEntry: PageEntry = {
        name: page.name,
        href: makeRelative(page.href),
        isSelected: page.href === highlightedHref.value
      }

      if (pageEntry.isSelected) {
        sectionEntry.isOpen = true
      }

      sectionEntry.children.push(pageEntry)
    }

    sectionEntry.isOpen = sectionOpenStates.value.get(sectionEntry.name) ?? sectionEntry.isOpen

    output.children.push(sectionEntry)
  }

  return output
})

onMounted(() => {
  fetch(props.listingSrc)
    .then((result) => {
      if (!result.ok) {
        throw new Error(`Couldn't load navigation data. Status: ${result.statusText}`)
      }

      return result.json()
    })
    .then((decoded) => {
      navigation.value = decoded
    })
    .catch((failedReason) => {
      error.value = `Loading content failed: ${failedReason}`
    })
    .finally(() => {
      loading.value = false
    })
})

// Updates the current page to bet the selected one.
function setCurrentPage(page: string) {
  currentPage.value = page
}

// Switches the open state of the given section.
function toggleSection(sectionName: string, isOpen: boolean) {
  sectionOpenStates.value.set(sectionName, !isOpen)
}
</script>

<template>
  <section class="_sidebar" style="padding-top: 0">
    <h1 v-if="loading">Loading...</h1>
    <h1 v-if="error">Error: {{ error }}</h1>
    <div role="navigation" class="_list">
      <a
        :href="displayNavigation.href"
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
          tabindex="-1"
          @click="toggleSection(section.name, section.isOpen)"
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
            tabindex="-1"
            @click="setCurrentPage(page.href)"
            >{{ page.name }}</a
          >
        </div>
      </div>

      <a :href="displayNavigation.licenseHref" class="_list-item _list-dir">
        <span class="_list-text">Open Source Licenses</span>
      </a>
    </div>
  </section>

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
/* Style overrides for strange DevDocs behavior. */
._list-dir {
  padding-left: 0 !important;
}
</style>
