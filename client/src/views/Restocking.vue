<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Budget card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetTitle') }}</h3>
        </div>
        <div class="budget-body">
          <input
            type="range"
            class="budget-slider"
            min="0"
            :max="maxBudget"
            step="25"
            v-model.number="budget"
          />
          <div class="budget-display">{{ currencySymbol }}{{ formatMoney(budget) }}</div>
          <div class="budget-readouts">
            <div class="budget-readout">
              <span class="readout-label">{{ t('restocking.budgetUsed') }}</span>
              <span class="readout-value used">{{ currencySymbol }}{{ formatMoney(budgetUsed) }}</span>
            </div>
            <div class="budget-readout">
              <span class="readout-label">{{ t('restocking.budgetRemaining') }}</span>
              <span class="readout-value remaining">{{ currencySymbol }}{{ formatMoney(budgetRemaining) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Success banner -->
      <div v-if="placedOrder" class="success-banner">
        <p class="banner-primary">{{ t('restocking.orderPlaced', { orderNumber: placedOrder.order_number }) }}</p>
        <p class="banner-secondary">{{ t('restocking.orderSummary', { days: placedOrder.lead_time_days, date: formatDate(placedOrder.expected_delivery) }) }}</p>
        <router-link to="/orders" class="banner-link">{{ t('restocking.viewInOrders') }}</router-link>
      </div>

      <!-- Recommendations card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ recommendations.length }})</h3>
        </div>
        <div v-if="recommendations.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.shortfall') }}</th>
                <th>{{ t('restocking.table.orderQty') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
                <th>{{ t('restocking.table.fill') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ item.shortfall }}</td>
                <td><strong>{{ item.qty }}</strong></td>
                <td>{{ currencySymbol }}{{ formatMoney(item.unit_cost) }}</td>
                <td><strong>{{ currencySymbol }}{{ formatMoney(item.line_cost) }}</strong></td>
                <td>{{ t('orders.leadTimeDays', { days: item.lead_time_days }) }}</td>
                <td>
                  <span v-if="!item.partial" class="badge success">{{ t('restocking.fullFill') }}</span>
                  <span v-else class="badge warning">{{ t('restocking.partialFill') }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Action bar -->
        <div class="action-bar">
          <span class="action-total">
            {{ t('restocking.budgetUsed') }}: <strong>{{ currencySymbol }}{{ formatMoney(budgetUsed) }}</strong>
          </span>
          <button
            class="btn-primary"
            :disabled="recommendations.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ t(submitting ? 'restocking.placingOrder' : 'restocking.placeOrder') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(0)
    const submitting = ref(false)
    const placedOrder = ref(null)
    let budgetInitialized = false

    // Items where forecasted demand exceeds current demand, sorted by shortfall DESC then sku ASC
    const shortfallItems = computed(() => {
      return forecasts.value
        .filter(f => f.forecasted_demand - f.current_demand > 0)
        .map(f => ({
          sku: f.item_sku,
          name: f.item_name,
          shortfall: f.forecasted_demand - f.current_demand,
          unit_cost: f.unit_cost,
          lead_time_days: f.lead_time_days
        }))
        .sort((a, b) => {
          if (b.shortfall !== a.shortfall) return b.shortfall - a.shortfall
          return a.sku.localeCompare(b.sku)
        })
    })

    // Total cost of all shortfalls rounded up to nearest 500
    const maxBudget = computed(() => {
      const total = shortfallItems.value.reduce(
        (sum, item) => sum + item.shortfall * item.unit_cost,
        0
      )
      if (total === 0) return 1000
      return Math.ceil(total / 500) * 500
    })

    // Greedy walk: allocate as much of each item as the remaining budget allows
    const recommendations = computed(() => {
      let remaining = budget.value
      const result = []
      for (const item of shortfallItems.value) {
        const qty = Math.min(item.shortfall, Math.floor(remaining / item.unit_cost))
        if (qty <= 0) continue
        const line_cost = qty * item.unit_cost
        result.push({
          sku: item.sku,
          name: item.name,
          shortfall: item.shortfall,
          qty,
          unit_cost: item.unit_cost,
          line_cost,
          lead_time_days: item.lead_time_days,
          partial: qty < item.shortfall
        })
        remaining -= line_cost
      }
      return result
    })

    const budgetUsed = computed(() =>
      recommendations.value.reduce((sum, r) => sum + r.line_cost, 0)
    )

    const budgetRemaining = computed(() => budget.value - budgetUsed.value)

    const maxLeadTime = computed(() => {
      if (recommendations.value.length === 0) return 0
      return Math.max(...recommendations.value.map(r => r.lead_time_days))
    })

    const loadForecasts = async () => {
      try {
        loading.value = true
        error.value = null
        forecasts.value = await api.getDemandForecasts()
        if (!budgetInitialized) {
          budget.value = maxBudget.value / 2
          budgetInitialized = true
        }
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const formatMoney = (value) => {
      return value.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    }

    const formatDate = (dateString) => {
      const { currentLocale } = useI18n()
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const placeOrder = async () => {
      if (recommendations.value.length === 0 || submitting.value) return
      submitting.value = true
      error.value = null
      try {
        const response = await api.createRestockOrder({
          budget: budget.value,
          items: recommendations.value.map(r => ({ sku: r.sku, quantity: r.qty }))
        })
        placedOrder.value = response
      } catch (err) {
        error.value = 'Failed to place restock order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      t,
      loading,
      error,
      forecasts,
      budget,
      submitting,
      placedOrder,
      shortfallItems,
      maxBudget,
      recommendations,
      budgetUsed,
      budgetRemaining,
      maxLeadTime,
      currencySymbol,
      translateProductName,
      formatMoney,
      formatDate,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-body {
  padding: 0.25rem 0 0.5rem;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  margin-bottom: 1rem;
  cursor: pointer;
}

.budget-display {
  font-size: 2.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.03em;
  margin-bottom: 1.25rem;
}

.budget-readouts {
  display: flex;
  gap: 2.5rem;
}

.budget-readout {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.readout-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.readout-value {
  font-size: 1.125rem;
  font-weight: 700;
}

.readout-value.used {
  color: #2563eb;
}

.readout-value.remaining {
  color: #059669;
}

.success-banner {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.25rem;
}

.banner-primary {
  font-weight: 600;
  color: #16a34a;
  margin-bottom: 0.25rem;
}

.banner-secondary {
  font-size: 0.875rem;
  color: #166534;
  margin-bottom: 0.75rem;
}

.banner-link {
  display: inline-block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #16a34a;
  text-decoration: underline;
}

.banner-link:hover {
  color: #15803d;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 1.5rem;
  padding-top: 1rem;
  margin-top: 0.75rem;
  border-top: 1px solid #e2e8f0;
}

.action-total {
  font-size: 0.875rem;
  color: #64748b;
}

.btn-primary {
  background: #2563eb;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 0.625rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
