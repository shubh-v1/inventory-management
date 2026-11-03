<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div v-if="candidates.length === 0" class="card empty-state">
        {{ t('restocking.noShortfall') }}
      </div>

      <template v-else>
        <div class="card budget-card">
          <div class="budget-header">
            <label for="restock-budget" class="budget-label">{{ t('restocking.budget') }}</label>
            <span class="budget-value">{{ formatMoney(budget) }}</span>
          </div>
          <input
            id="restock-budget"
            v-model.number="budget"
            type="range"
            class="budget-slider"
            min="0"
            :max="maxBudget"
            :step="BUDGET_STEP"
          />
          <div class="budget-scale">
            <span>{{ formatMoney(0) }}</span>
            <span>{{ formatMoney(maxBudget) }}</span>
          </div>
          <p class="budget-hint">{{ t('restocking.budgetHint') }}</p>
        </div>

        <div class="stats-grid">
          <div class="stat-card info">
            <div class="stat-label">{{ t('restocking.totalCost') }}</div>
            <div class="stat-value">{{ formatMoney(totalCost) }}</div>
          </div>
          <div class="stat-card success">
            <div class="stat-label">{{ t('restocking.budgetRemaining') }}</div>
            <div class="stat-value">{{ formatMoney(budgetRemaining) }}</div>
          </div>
          <div class="stat-card warning">
            <div class="stat-label">{{ t('restocking.longestLeadTime') }}</div>
            <div class="stat-value">
              {{ longestLeadTime !== null ? t('restocking.days', { count: longestLeadTime }) : '—' }}
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="card-title">
              {{ t('restocking.recommendations') }}
              <span class="funded-count">{{ t('restocking.itemsFunded', { funded: fundedItems.length, total: recommendations.length }) }}</span>
            </h3>
            <button
              type="button"
              class="place-order-button"
              :disabled="fundedItems.length === 0 || submitting"
              @click="placeOrder"
            >
              {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
            </button>
          </div>

          <div v-if="submitError" class="error">{{ submitError }}</div>
          <div v-if="submittedOrder" class="success-message">
            {{ t('restocking.orderPlaced', { orderNumber: submittedOrder.order_number }) }}
            <router-link to="/orders" class="success-link">{{ t('restocking.viewOrders') }}</router-link>
          </div>

          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>{{ t('restocking.table.sku') }}</th>
                  <th>{{ t('restocking.table.item') }}</th>
                  <th>{{ t('restocking.table.trend') }}</th>
                  <th class="num">{{ t('restocking.table.onHand') }}</th>
                  <th class="num">{{ t('restocking.table.forecast') }}</th>
                  <th class="num">{{ t('restocking.table.recommendedQty') }}</th>
                  <th class="num">{{ t('restocking.table.unitCost') }}</th>
                  <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                  <th class="num">{{ t('restocking.table.leadTime') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in recommendations"
                  :key="item.sku"
                  :class="{ 'not-funded': item.quantity === 0 }"
                >
                  <td><strong>{{ item.sku }}</strong></td>
                  <td>{{ translateProductName(item.name) }}</td>
                  <td>
                    <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                  </td>
                  <td class="num">{{ item.onHand }}</td>
                  <td class="num">{{ item.forecast }}</td>
                  <td class="num">
                    <strong v-if="item.quantity > 0">{{ item.quantity }}</strong>
                    <span v-else class="not-funded-label">{{ t('restocking.notFunded') }}</span>
                    <span v-if="item.quantity > 0 && item.quantity < item.shortfall" class="partial-note">
                      / {{ item.shortfall }}
                    </span>
                  </td>
                  <td class="num">{{ formatMoney(item.unitCost, 2) }}</td>
                  <td class="num">{{ item.quantity > 0 ? formatMoney(item.lineTotal, 2) : '—' }}</td>
                  <td class="num">{{ item.leadTime !== null ? t('restocking.days', { count: item.leadTime }) : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const BUDGET_STEP = 500
// Trends that get funded ahead of everything else
const PRIORITY_TREND = 'increasing'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const inventoryItems = ref([])
    const budget = ref(0)

    const submitting = ref(false)
    const submitError = ref(null)
    const submittedOrder = ref(null)

    // Forecasts joined with inventory (on-hand qty, cost, lead time) by SKU.
    // Forecasts without a matching inventory item can't be priced, so they are dropped.
    const candidates = computed(() => {
      const inventoryBySku = new Map(inventoryItems.value.map(item => [item.sku, item]))
      return forecasts.value
        .map(forecast => {
          const item = inventoryBySku.get(forecast.item_sku)
          if (!item) return null
          const shortfall = Math.max(0, forecast.forecasted_demand - item.quantity_on_hand)
          return {
            sku: item.sku,
            name: item.name || forecast.item_name,
            trend: forecast.trend,
            onHand: item.quantity_on_hand,
            forecast: forecast.forecasted_demand,
            shortfall,
            unitCost: item.unit_cost,
            leadTime: Number.isFinite(item.lead_time_days) ? item.lead_time_days : null
          }
        })
        .filter(row => row && row.shortfall > 0 && row.unitCost > 0)
    })

    // Slider ceiling: cost of covering every shortfall, rounded up to the next step
    const maxBudget = computed(() => {
      const fullCost = candidates.value.reduce((sum, row) => sum + row.shortfall * row.unitCost, 0)
      return Math.ceil(fullCost / BUDGET_STEP) * BUDGET_STEP
    })

    // Ranking: increasing-trend items first, then by shortfall value (shortfall x unit cost) desc.
    // Budget fill is strictly in that order: each item gets its full shortfall while it fits;
    // the first item that doesn't fit gets as many units as the remainder buys and funding stops
    // there, so lower-priority items never jump ahead of a higher-priority one.
    const recommendations = computed(() => {
      const ranked = [...candidates.value].sort((a, b) => {
        const aPriority = a.trend === PRIORITY_TREND ? 0 : 1
        const bPriority = b.trend === PRIORITY_TREND ? 0 : 1
        if (aPriority !== bPriority) return aPriority - bPriority
        return b.shortfall * b.unitCost - a.shortfall * a.unitCost
      })

      let remaining = budget.value
      let exhausted = false
      return ranked.map(row => {
        let quantity = 0
        if (!exhausted) {
          const fullCost = row.shortfall * row.unitCost
          // Small epsilon guards against float error on exact-fit costs (e.g. 24.99 * n)
          if (fullCost <= remaining + 1e-6) {
            quantity = row.shortfall
          } else {
            quantity = Math.floor((remaining + 1e-6) / row.unitCost)
            exhausted = true
          }
        }
        const lineTotal = Math.round(quantity * row.unitCost * 100) / 100
        remaining -= lineTotal
        return { ...row, quantity, lineTotal }
      })
    })

    const fundedItems = computed(() => recommendations.value.filter(row => row.quantity > 0))

    const totalCost = computed(() => {
      return Math.round(fundedItems.value.reduce((sum, row) => sum + row.lineTotal, 0) * 100) / 100
    })

    const budgetRemaining = computed(() => Math.max(0, budget.value - totalCost.value))

    const longestLeadTime = computed(() => {
      const leadTimes = fundedItems.value.map(row => row.leadTime).filter(days => days !== null)
      return leadTimes.length ? Math.max(...leadTimes) : null
    })

    const formatMoney = (amount, decimals = 0) => {
      return formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)
    }

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        const [forecastsData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory()
        ])
        forecasts.value = forecastsData
        inventoryItems.value = inventoryData
        // Default to ~50% of the ceiling, snapped to the slider step
        budget.value = Math.round(maxBudget.value / 2 / BUDGET_STEP) * BUDGET_STEP
      } catch (err) {
        error.value = t('restocking.loadFailed') + ': ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (fundedItems.value.length === 0 || submitting.value) return
      try {
        submitting.value = true
        submitError.value = null
        submittedOrder.value = null
        submittedOrder.value = await api.createRestockOrder({
          items: fundedItems.value.map(row => ({
            sku: row.sku,
            name: row.name,
            quantity: row.quantity,
            unit_cost: row.unitCost
          })),
          budget: budget.value
        })
      } catch (err) {
        // FastAPI returns a string detail for 400/404 and an array for 422 validation errors
        const detail = err.response?.data?.detail
        submitError.value = typeof detail === 'string' ? detail : t('restocking.orderFailed')
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadData)

    return {
      t,
      translateProductName,
      BUDGET_STEP,
      loading,
      error,
      budget,
      maxBudget,
      candidates,
      recommendations,
      fundedItems,
      totalCost,
      budgetRemaining,
      longestLeadTime,
      submitting,
      submitError,
      submittedOrder,
      formatMoney,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: 1.5rem;
}

.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.budget-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.budget-slider {
  width: 100%;
  accent-color: #3b82f6;
  cursor: pointer;
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.budget-hint {
  margin-top: 0.75rem;
  font-size: 0.813rem;
  color: #64748b;
}

.funded-count {
  margin-left: 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #64748b;
  letter-spacing: normal;
}

.place-order-button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  background: #3b82f6;
  color: white;
}

.place-order-button:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.place-order-button:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.success-message {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}

.success-link {
  margin-left: 0.5rem;
  color: #059669;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  color: #64748b;
  padding: 3rem;
}

th.num,
td.num {
  text-align: right;
}

tr.not-funded td {
  color: #94a3b8;
}

tr.not-funded .badge {
  opacity: 0.6;
}

.not-funded-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  color: #94a3b8;
}

.partial-note {
  color: #64748b;
  font-size: 0.813rem;
}
</style>
