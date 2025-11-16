<template>
  <section class="section-card">
    <header class="section-card__header">
      <div>
        <p v-if="kicker" class="section-card__kicker">{{ kicker }}</p>
        <h2>{{ title }}</h2>
        <p v-if="description" class="section-card__description">
          {{ description }}
        </p>
      </div>
      <div v-if="icon" class="section-card__icon">
        <span>{{ icon }}</span>
      </div>
    </header>
    <div class="section-card__content">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="section-card__footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  kicker?: string
  icon?: string
}>()
</script>

<style scoped>
.section-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 1.5rem;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.section-card__kicker {
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.section-card__description {
  color: var(--text-secondary);
  margin-top: 0.25rem;
}

.section-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--bg-secondary);
  display: grid;
  place-items: center;
  font-weight: 600;
}

.section-card__content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-card__footer {
  border-top: 1px solid var(--border-color);
  padding-top: 1rem;
}
</style>
