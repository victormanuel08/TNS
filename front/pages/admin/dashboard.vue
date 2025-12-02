<template>
  <div class="admin-dashboard">
    <header class="admin-header">
      <div class="header-content">
        <div class="header-brand">
          <div class="brand-logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div>
            <h1>EDDESO</h1>
            <p class="header-subtitle">Panel de Administración</p>
          </div>
        </div>
        <div class="header-actions">
          <span class="user-info">{{ user?.username }}</span>
          <button @click="handleLogout" class="btn-logout">Cerrar Sesión</button>
        </div>
      </div>
    </header>

    <nav class="admin-nav">
      <button
        v-for="section in sections"
        :key="section.id"
        class="nav-btn"
        :class="{ active: activeSection === section.id }"
        @click="activeSection = section.id"
      >
        <span class="nav-icon" v-html="section.icon"></span>
        <span>{{ section.name }}</span>
      </button>
    </nav>

    <main class="admin-main">
      <!-- Servidores -->
      <section v-if="activeSection === 'servidores'" class="section">
        <div class="section-header">
          <h2>Gestión de Servidores</h2>
          <div class="actions-bar">
            <button class="btn-primary" @click="showCreateServer = true">
              <span>+</span> Crear Servidor
            </button>
            <button class="btn-secondary" @click="loadServers" :disabled="loadingServers">
              <span v-if="loadingServers">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingServers" class="loading-state">
          <p>Cargando servidores...</p>
        </div>
        
        <div v-else-if="servers.length === 0" class="empty-state">
          <p>No hay servidores registrados</p>
        </div>
        
        <div v-else class="servers-grid">
          <div v-for="server in servers" :key="server.id" class="server-card">
            <div class="server-header">
              <h3>{{ server.nombre }}</h3>
              <span class="server-badge" :class="`badge-${server.tipo_servidor?.toLowerCase()}`">
                {{ server.tipo_servidor }}
              </span>
            </div>
            <div class="server-info">
              <p class="info-item">
                <span class="info-label">Host:</span>
                <span class="info-value">{{ server.host }}</span>
              </p>
              <p class="info-item" v-if="server.puerto">
                <span class="info-label">Puerto:</span>
                <span class="info-value">{{ server.puerto }}</span>
              </p>
              <p class="info-item">
                <span class="info-label">Usuario:</span>
                <span class="info-value">{{ server.usuario }}</span>
              </p>
            </div>
            <div class="server-actions">
              <button 
                class="btn-small btn-primary" 
                @click="scanEmpresas(server.id)" 
                :disabled="scanningServer === server.id"
                :title="activeScanTasks[server.id] ? 'Hay un proceso en curso. Haz clic para ver el progreso.' : 'Escanear empresas en este servidor'"
              >
                <svg v-if="scanningServer === server.id" class="spinner-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                </svg>
                <svg v-else-if="activeScanTasks[server.id]" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
                {{ activeScanTasks[server.id] ? 'Ver Progreso' : 'Escanear Empresas' }}
              </button>
              <button class="btn-small btn-secondary" @click="editServer(server)">Editar</button>
              <button class="btn-small btn-info" @click="viewServerDetails(server.id)">Detalles</button>
              <button class="btn-small btn-danger" @click="deleteServer(server.id)">Eliminar</button>
            </div>
          </div>
        </div>
      </section>

      <!-- Empresas -->
      <section v-if="activeSection === 'empresas'" class="section">
        <div class="section-header">
          <h2>Empresas</h2>
          <div class="actions-bar">
            <input
              v-model="empresaSearch"
              type="text"
              placeholder="Buscar por nombre, NIT o código..."
              class="search-input"
            />
            <select v-model="empresaFilterServidor" class="filter-select">
              <option value="">Todos los servidores</option>
              <option v-for="server in servers" :key="server.id" :value="server.id">
                {{ server.nombre }}
              </option>
            </select>
            <select v-model="empresaFilterEstado" class="filter-select">
              <option value="">Todos los estados</option>
              <option value="ACTIVO">Activo</option>
              <option value="INACTIVO">Inactivo</option>
              <option value="MANTENIMIENTO">Mantenimiento</option>
            </select>
            <button class="btn-secondary" @click="loadEmpresas" :disabled="loadingEmpresas">
              <span v-if="loadingEmpresas">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingEmpresas" class="loading-state">
          <p>Cargando empresas...</p>
        </div>
        
        <div v-else-if="paginatedEmpresas.length === 0" class="empty-state">
          <p>No hay empresas que coincidan con los filtros</p>
        </div>
        
        <div v-else>
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th class="sortable" @click="sortEmpresas('nombre')">
                    Nombre
                    <span v-if="empresaSortField === 'nombre'" class="sort-icon">
                      {{ empresaSortOrder === 'asc' ? '↑' : '↓' }}
                    </span>
                  </th>
                  <th class="sortable" @click="sortEmpresas('nit')">
                    NIT
                    <span v-if="empresaSortField === 'nit'" class="sort-icon">
                      {{ empresaSortOrder === 'asc' ? '↑' : '↓' }}
                    </span>
                  </th>
                  <th class="sortable" @click="sortEmpresas('anio_fiscal')">
                    Año Fiscal
                    <span v-if="empresaSortField === 'anio_fiscal'" class="sort-icon">
                      {{ empresaSortOrder === 'asc' ? '↑' : '↓' }}
                    </span>
                  </th>
                  <th class="sortable" @click="sortEmpresas('codigo')">
                    Código
                    <span v-if="empresaSortField === 'codigo'" class="sort-icon">
                      {{ empresaSortOrder === 'asc' ? '↑' : '↓' }}
                    </span>
                  </th>
                  <th class="sortable" @click="sortEmpresas('servidor_nombre')">
                    Servidor
                    <span v-if="empresaSortField === 'servidor_nombre'" class="sort-icon">
                      {{ empresaSortOrder === 'asc' ? '↑' : '↓' }}
                    </span>
                  </th>
                  <th class="sortable" @click="sortEmpresas('estado')">
                    Estado
                    <span v-if="empresaSortField === 'estado'" class="sort-icon">
                      {{ empresaSortOrder === 'asc' ? '↑' : '↓' }}
                    </span>
                  </th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="empresa in paginatedEmpresas" :key="empresa.id">
                  <td><strong>{{ empresa.nombre }}</strong></td>
                  <td>{{ empresa.nit || '-' }}</td>
                  <td>{{ empresa.anio_fiscal }}</td>
                  <td><code>{{ empresa.codigo }}</code></td>
                  <td>{{ empresa.servidor_nombre || '-' }}</td>
                  <td>
                    <span class="status-badge" :class="empresa.estado === 'ACTIVO' ? 'status-active' : (empresa.estado === 'INACTIVO' ? 'status-inactive' : 'status-warning')">
                      {{ empresa.estado || 'ACTIVO' }}
                    </span>
                  </td>
                  <td>
                    <div class="action-buttons">
                      <button class="btn-small btn-primary" @click="openExtractDataModal(empresa)" title="Extraer datos">
                        📥 Extraer Datos
                      </button>
                      <button class="btn-small btn-info" @click="viewEmpresaDetails(empresa.id)" title="Ver detalles">
                        👁️
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- Paginación -->
          <div class="pagination">
            <div class="pagination-info">
              Mostrando {{ (empresaCurrentPage - 1) * empresaPageSize + 1 }} - {{ Math.min(empresaCurrentPage * empresaPageSize, sortedAndFilteredEmpresas.length) }} de {{ sortedAndFilteredEmpresas.length }} empresas
            </div>
            <div class="pagination-controls">
              <button 
                class="btn-small btn-secondary" 
                @click="empresaCurrentPage = 1" 
                :disabled="empresaCurrentPage === 1"
              >
                ««
              </button>
              <button 
                class="btn-small btn-secondary" 
                @click="empresaCurrentPage--" 
                :disabled="empresaCurrentPage === 1"
              >
                «
              </button>
              <span class="page-info">Página {{ empresaCurrentPage }} de {{ empresaTotalPages }}</span>
              <button 
                class="btn-small btn-secondary" 
                @click="empresaCurrentPage++" 
                :disabled="empresaCurrentPage >= empresaTotalPages"
              >
                »
              </button>
              <button 
                class="btn-small btn-secondary" 
                @click="empresaCurrentPage = empresaTotalPages" 
                :disabled="empresaCurrentPage >= empresaTotalPages"
              >
                »»
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Usuarios -->
      <section v-if="activeSection === 'usuarios'" class="section">
        <div class="section-header">
          <h2>Gestión de Usuarios</h2>
          <div class="actions-bar">
            <input
              v-model="userSearch"
              type="text"
              placeholder="Buscar usuarios..."
              class="search-input"
            />
            <button class="btn-primary" @click="showCreateUser = true">
              <span>+</span> Crear Usuario
            </button>
            <button class="btn-secondary" @click="loadUsers" :disabled="loadingUsers">
              <span v-if="loadingUsers">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>

        <div v-if="loadingUsers" class="loading-state">
          <p>Cargando usuarios...</p>
        </div>

        <div v-else-if="filteredUsers.length === 0" class="empty-state">
          <p>No hay usuarios</p>
        </div>

        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Usuario</th>
                <th>Email</th>
                <th>Nombre</th>
                <th>Superusuario</th>
                <th>Staff</th>
                <th>Activo</th>
                <th>Último Login</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="usr in filteredUsers" :key="usr.id">
                <td>{{ usr.id }}</td>
                <td><strong>{{ usr.username }}</strong></td>
                <td>{{ usr.email || '-' }}</td>
                <td>{{ (usr.first_name + ' ' + usr.last_name).trim() || '-' }}</td>
                <td>
                  <span class="status-badge" :class="usr.is_superuser ? 'status-active' : 'status-inactive'">
                    {{ usr.is_superuser_display }}
                  </span>
                </td>
                <td>
                  <span class="status-badge" :class="usr.is_staff ? 'status-active' : 'status-inactive'">
                    {{ usr.is_staff_display }}
                  </span>
                </td>
                <td>
                  <span class="status-badge" :class="usr.is_active ? 'status-active' : 'status-inactive'">
                    {{ usr.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td>{{ usr.last_login_formatted || 'Nunca' }}</td>
                <td>
                  <div class="action-buttons">
                    <button class="btn-small btn-secondary" @click="editUser(usr)" title="Editar">
                      ✏️
                    </button>
                    <button class="btn-small btn-warning" @click="resetUserPassword(usr)" title="Resetear Contraseña">
                      🔑
                    </button>
                    <button 
                      class="btn-small btn-danger" 
                      @click="deleteUser(usr)" 
                      title="Eliminar"
                      :disabled="usr.id === user?.id"
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- API Keys -->
      <section v-if="activeSection === 'api-keys'" class="section">
        <div class="section-header">
          <h2>Gestión de API Keys</h2>
          <div class="actions-bar">
            <button class="btn-primary" @click="showCreateApiKey = true">
              <span>+</span> Generar API Key
            </button>
            <button class="btn-secondary" @click="loadApiKeys" :disabled="loadingApiKeys">
              <span v-if="loadingApiKeys">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingApiKeys" class="loading-state">
          <p>Cargando API Keys...</p>
        </div>
        
        <div v-else-if="apiKeys.length === 0" class="empty-state">
          <p>No hay API Keys generadas</p>
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>NIT</th>
                <th>Cliente</th>
                <th>API Key</th>
                <th>Empresas Asociadas</th>
                <th>Estado</th>
                <th>Fecha Creación</th>
                <th>Fecha Caducidad</th>
                <th>Peticiones</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="key in apiKeys" :key="key.id">
                <td><code>{{ key.nit }}</code></td>
                <td><strong>{{ key.nombre_cliente }}</strong></td>
                <td>
                  <div class="api-key-cell">
                    <code v-if="!key.showKey" class="api-key-masked">{{ key.api_key_masked || '••••••••' }}</code>
                    <code v-else class="api-key-visible">{{ key.api_key }}</code>
                    <button 
                      class="btn-tiny btn-secondary" 
                      @click="toggleApiKeyVisibility(key.id)"
                      :title="key.showKey ? 'Ocultar' : 'Mostrar'"
                    >
                      {{ key.showKey ? '👁️' : '👁️‍🗨️' }}
                    </button>
                    <button 
                      class="btn-tiny btn-info" 
                      @click="copyApiKey(key.api_key)"
                      title="Copiar"
                    >
                      📋
                    </button>
                  </div>
                </td>
                <td>
                  <span class="badge">{{ key.empresas_asociadas_count || 0 }}</span>
                  <button 
                    v-if="key.empresas_asociadas_count > 0"
                    class="btn-tiny btn-info" 
                    @click="viewApiKeyEmpresas(key.id)"
                    title="Ver empresas"
                  >
                    👁️
                  </button>
                </td>
                <td>
                  <span class="status-badge" :class="key.activa && !key.expirada ? 'status-active' : 'status-inactive'">
                    {{ key.activa && !key.expirada ? 'Activa' : (key.expirada ? 'Expirada' : 'Inactiva') }}
                  </span>
                </td>
                <td>{{ formatDate(key.fecha_creacion) }}</td>
                <td>
                  <span :class="key.expirada ? 'text-danger' : ''">
                    {{ formatDate(key.fecha_caducidad) }}
                  </span>
                </td>
                <td>{{ key.contador_peticiones || 0 }}</td>
                <td>
                  <div class="action-buttons">
                    <button 
                      class="btn-small btn-primary" 
                      @click="regenerateApiKey(key.id)"
                      title="Regenerar"
                    >
                      🔄
                    </button>
                    <button 
                      class="btn-small btn-secondary" 
                      @click="toggleApiKeyStatus(key.id, !key.activa)"
                      :title="key.activa ? 'Desactivar' : 'Activar'"
                    >
                      {{ key.activa ? '⏸️' : '▶️' }}
                    </button>
                    <button 
                      class="btn-small btn-danger" 
                      @click="revokeApiKey(key.id)"
                      title="Revocar"
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Scrapers -->
      <section v-if="activeSection === 'scrapers'" class="section">
        <div class="section-header">
          <h2>Scrapers</h2>
        </div>
        <div class="scrapers-grid">
          <div class="scraper-card">
            <div class="scraper-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
            </div>
            <h3>DIAN Scraper</h3>
            <p>Scraping automático de facturas desde DIAN</p>
            <button class="btn-primary" @click="navigateToScraper('/dian')">Gestionar</button>
          </div>
          <div class="scraper-card">
            <div class="scraper-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
            </div>
            <h3>FUDO Scraper</h3>
            <p>Scraping automático desde FUDO</p>
            <button class="btn-primary" @click="navigateToScraper('/fudo')">Gestionar</button>
          </div>
        </div>
      </section>

      <!-- ML Models -->
      <section v-if="activeSection === 'ml'" class="section">
        <div class="section-header">
          <h2>Modelos de Machine Learning</h2>
          <div class="actions-bar">
            <select v-model="mlFilterEmpresa" class="filter-select">
              <option value="">Todas las empresas</option>
              <option v-for="empresa in empresas" :key="empresa.id" :value="empresa.id">
                {{ empresa.nombre }} ({{ empresa.nit }})
              </option>
            </select>
            <button class="btn-secondary" @click="loadMLModels" :disabled="loadingML">
              <span v-if="loadingML">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingML" class="loading-state">
          <p>Cargando modelos...</p>
        </div>
        
        <div v-else-if="filteredMLModels.length === 0" class="empty-state">
          <p>No hay modelos entrenados</p>
          <p style="margin-top: 1rem; color: #666;">Selecciona una empresa y haz clic en "Entrenar Modelo" para comenzar</p>
        </div>
        
        <div v-else class="models-grid">
          <div v-for="model in filteredMLModels" :key="model.id" class="model-card">
            <div class="model-header">
              <h3>{{ model.nombre || `Modelo ${model.nit_empresa}` }}</h3>
              <span class="model-badge">NIT: {{ model.nit_empresa }}</span>
            </div>
            <div class="model-info">
              <p><strong>Fecha entrenamiento:</strong> {{ formatDate(model.fecha_entrenamiento) }}</p>
              <p><strong>Filas de entrenamiento:</strong> {{ model.filas_entrenamiento || 0 }}</p>
              <p v-if="model.mlflow_run_id"><strong>MLflow Run ID:</strong> <code>{{ model.mlflow_run_id }}</code></p>
            </div>
            <div class="model-actions">
              <button 
                class="btn-small btn-primary" 
                @click="trainModel(model.empresa_servidor_id_original || model.empresa_servidor_id)"
                :disabled="trainingModel === (model.empresa_servidor_id_original || model.empresa_servidor_id)"
              >
                <span v-if="trainingModel === (model.empresa_servidor_id_original || model.empresa_servidor_id)">⟳</span>
                <span v-else>🔄 Re-entrenar</span>
              </button>
              <button 
                v-if="model.mlflow_ui_url" 
                class="btn-small btn-info" 
                @click="window.open(model.mlflow_ui_url, '_blank')"
              >
                📊 Ver en MLflow
              </button>
            </div>
          </div>
        </div>
        
        <!-- Botón para entrenar nuevo modelo -->
        <div v-if="empresas.length > 0" class="section-footer" style="margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e5e7eb;">
          <h3 style="margin-bottom: 1rem;">Entrenar Nuevo Modelo</h3>
          <div class="form-row" style="max-width: 600px;">
            <div class="form-group">
              <label>Seleccionar Empresa *</label>
              <select v-model="newModelEmpresaId" class="form-input" required>
                <option value="">Seleccionar empresa...</option>
                <option v-for="empresa in empresas" :key="empresa.id" :value="empresa.id">
                  {{ empresa.nombre }} ({{ empresa.nit }}) - Año {{ empresa.anio_fiscal }}
                </option>
              </select>
            </div>
            <div class="form-group" style="display: flex; align-items: flex-end;">
              <button 
                class="btn-primary" 
                @click="trainModel(newModelEmpresaId)"
                :disabled="!newModelEmpresaId || trainingModel === newModelEmpresaId"
              >
                <span v-if="trainingModel === newModelEmpresaId">⟳</span>
                <span v-else>🚀 Entrenar Modelo</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- VPN -->
      <section v-if="activeSection === 'vpn'" class="section">
        <div class="section-header">
          <h2>Gestión de VPN (WireGuard)</h2>
          <div class="actions-bar">
            <button class="btn-primary" @click="showCreateVpn = true">
              <span>+</span> Crear Túnel
            </button>
            <button class="btn-secondary" @click="syncPeers" :disabled="loadingVpn || syncingPeers" title="Sincronizar peers existentes del servidor">
              <span v-if="syncingPeers">⟳</span>
              <span v-else>🔄</span>
              Sincronizar
            </button>
            <button class="btn-secondary" @click="loadVpnConfigs" :disabled="loadingVpn">
              <span v-if="loadingVpn">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingVpn" class="loading-state">
          <p>Cargando configuraciones VPN...</p>
        </div>
        
        <div v-else-if="vpnConfigs.length === 0" class="empty-state">
          <p>No hay configuraciones VPN creadas</p>
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>IP Asignada</th>
                <th>Estado</th>
                <th>Conexión</th>
                <th>Tráfico</th>
                <th>Último Handshake</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="config in vpnConfigs" :key="config.id">
                <td>
                  <div class="name-cell">
                    <span v-if="editingNameId !== config.id" @dblclick="startEditName(config.id, config.nombre)" class="editable-name">
                      <strong>{{ config.nombre }}</strong>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="edit-icon">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </span>
                    <div v-else class="edit-name-input">
                      <input 
                        v-model="editingNameValue" 
                        @blur="saveName(config.id)"
                        @keyup.enter="saveName(config.id)"
                        @keyup.esc="cancelEditName"
                        class="inline-input"
                        ref="nameInput"
                      />
                    </div>
                  </div>
                </td>
                <td><code>{{ config.ip_address || '-' }}</code></td>
                <td>
                  <span class="status-badge" :class="config.activo ? 'status-active' : 'status-inactive'">
                    {{ config.activo ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td>
                  <span v-if="config.stats" class="connection-status" :class="config.stats.connected ? 'connected' : 'disconnected'">
                    <span class="status-dot"></span>
                    {{ config.stats.connected ? 'Conectado' : 'Desconectado' }}
                  </span>
                  <span v-else class="connection-status unknown">
                    <span class="status-dot"></span>
                    Desconocido
                  </span>
                </td>
                <td>
                  <div v-if="config.stats" class="traffic-info">
                    <div class="traffic-item">
                      <span class="traffic-label">↑</span>
                      <span class="traffic-value">{{ formatBytes(config.stats.tx_bytes) }}</span>
                    </div>
                    <div class="traffic-item">
                      <span class="traffic-label">↓</span>
                      <span class="traffic-value">{{ formatBytes(config.stats.rx_bytes) }}</span>
                    </div>
                  </div>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="config.stats && config.stats.last_handshake_seconds_ago !== null" class="handshake-time">
                    {{ formatHandshakeTime(config.stats.last_handshake_seconds_ago) }}
                  </span>
                  <span v-else class="handshake-time never">Nunca</span>
                </td>
                <td>
                  <div class="action-buttons">
                    <button class="btn-small btn-info" @click="viewStats(config.id)" title="Ver estadísticas">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <polyline points="12 6 12 12 16 14"/>
                      </svg>
                    </button>
                    <button class="btn-small btn-info" @click="readVpnConfig(config.id)" title="Leer config actual">
                      👁️
                    </button>
                    <button class="btn-small btn-primary" @click="downloadVpnConfig(config.id)" title="Descargar archivo .conf (regenera automáticamente)">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                      </svg>
                    </button>
                    <button class="btn-small btn-warning" @click="deleteVpnConfigFile(config.id)" title="Eliminar archivo .conf">
                      🗑️ Archivo
                    </button>
                    <button class="btn-small btn-secondary" @click="toggleVpnConfig(config.id, !config.activo)" :title="config.activo ? 'Desactivar' : 'Activar'">
                      {{ config.activo ? 'Desactivar' : 'Activar' }}
                    </button>
                    <button class="btn-small btn-danger" @click="deleteVpnConfig(config.id)" title="Eliminar configuración completa">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Servicios del Sistema -->
      <section v-if="activeSection === 'servicios'" class="section">
        <div class="section-header">
          <h2>Gestión de Servicios del Servidor</h2>
          <div class="actions-bar">
            <button class="btn-secondary" @click="loadSystemInfo" :disabled="loadingSystemInfo">
              <span v-if="loadingSystemInfo">⟳</span>
              <span v-else>↻</span>
              Actualizar Info
            </button>
            <button class="btn-secondary" @click="loadSystemdServices" :disabled="loadingSystemd">
              <span v-if="loadingSystemd">⟳</span>
              <span v-else>↻</span>
              Actualizar Systemd
            </button>
            <button class="btn-secondary" @click="loadPm2Processes" :disabled="loadingPm2">
              <span v-if="loadingPm2">⟳</span>
              <span v-else>↻</span>
              Actualizar PM2
            </button>
          </div>
        </div>

        <!-- Información del Sistema -->
        <div v-if="systemInfo" class="system-info-card">
          <h3>Información del Sistema</h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Uptime:</span>
              <span class="info-value">{{ systemInfo.uptime || 'N/A' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Load Average:</span>
              <span class="info-value">{{ systemInfo.load_average || 'N/A' }}</span>
            </div>
          </div>
          <div class="info-block" v-if="systemInfo.memory">
            <strong>Memoria:</strong>
            <pre>{{ systemInfo.memory }}</pre>
          </div>
          <div class="info-block" v-if="systemInfo.disk">
            <strong>Disco:</strong>
            <pre>{{ systemInfo.disk }}</pre>
          </div>
        </div>

        <!-- Tabs para Systemd y PM2 -->
        <div class="tabs">
          <button 
            class="tab-button" 
            :class="{ active: serviceTab === 'systemd' }"
            @click="serviceTab = 'systemd'"
          >
            Systemd Services
          </button>
          <button 
            class="tab-button" 
            :class="{ active: serviceTab === 'pm2' }"
            @click="serviceTab = 'pm2'"
          >
            PM2 Processes
          </button>
        </div>

        <!-- Systemd Services -->
        <div v-if="serviceTab === 'systemd'" class="tab-content">
          <div v-if="loadingSystemd" class="loading-state">
            <p>Cargando servicios systemd...</p>
          </div>
          <div v-else-if="systemdServices.length === 0" class="empty-state">
            <p>No se pudieron cargar los servicios systemd</p>
          </div>
          <div v-else class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Servicio</th>
                  <th>Descripción</th>
                  <th>Estado</th>
                  <th>Sub-Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="service in systemdServices" :key="service.name">
                  <td><strong>{{ service.name }}</strong></td>
                  <td>{{ service.description || '-' }}</td>
                  <td>
                    <span class="status-badge" :class="service.running ? 'status-active' : 'status-inactive'">
                      {{ service.active_state }}
                    </span>
                  </td>
                  <td>{{ service.sub_state }}</td>
                  <td>
                    <div class="action-buttons">
                      <button 
                        v-if="!service.running"
                        class="btn-small btn-primary" 
                        @click="systemdAction(service.name, 'start')"
                        title="Iniciar"
                      >
                        ▶
                      </button>
                      <button 
                        v-if="service.running"
                        class="btn-small btn-secondary" 
                        @click="systemdAction(service.name, 'stop')"
                        title="Detener"
                      >
                        ⏸
                      </button>
                      <button 
                        class="btn-small btn-secondary" 
                        @click="systemdAction(service.name, 'restart')"
                        title="Reiniciar"
                      >
                        ↻
                      </button>
                      <button 
                        class="btn-small btn-info" 
                        @click="viewServiceLogs(service.name, 'systemd')"
                        title="Ver Logs"
                      >
                        📋
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- PM2 Processes -->
        <div v-if="serviceTab === 'pm2'" class="tab-content">
          <div v-if="loadingPm2" class="loading-state">
            <p>Cargando procesos PM2...</p>
          </div>
          <div v-else-if="pm2Processes.length === 0" class="empty-state">
            <p>No hay procesos PM2 o PM2 no está instalado</p>
          </div>
          <div v-else class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Estado</th>
                  <th>CPU %</th>
                  <th>Memoria</th>
                  <th>Reinicios</th>
                  <th>Uptime</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="proc in pm2Processes" :key="proc.id">
                  <td>{{ proc.id }}</td>
                  <td><strong>{{ proc.name }}</strong></td>
                  <td>
                    <span class="status-badge" :class="proc.status === 'online' ? 'status-active' : 'status-inactive'">
                      {{ proc.status }}
                    </span>
                  </td>
                  <td>{{ proc.cpu?.toFixed(1) || '0.0' }}%</td>
                  <td>{{ formatBytes(proc.memory || 0) }}</td>
                  <td>{{ proc.restarts || 0 }}</td>
                  <td>{{ formatUptime(proc.uptime) }}</td>
                  <td>
                    <div class="action-buttons">
                      <button 
                        v-if="proc.status !== 'online'"
                        class="btn-small btn-primary" 
                        @click="pm2Action(proc.name, 'start')"
                        title="Iniciar"
                      >
                        ▶
                      </button>
                      <button 
                        v-if="proc.status === 'online'"
                        class="btn-small btn-secondary" 
                        @click="pm2Action(proc.name, 'stop')"
                        title="Detener"
                      >
                        ⏸
                      </button>
                      <button 
                        class="btn-small btn-secondary" 
                        @click="pm2Action(proc.name, 'restart')"
                        title="Reiniciar"
                      >
                        ↻
                      </button>
                      <button 
                        class="btn-small btn-info" 
                        @click="viewServiceLogs(proc.name, 'pm2')"
                        title="Ver Logs"
                      >
                        📋
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- Terminal SSH -->
      <!-- Logs -->
      <section v-if="activeSection === 'logs'" class="section">
        <div class="section-header">
          <h2>Logs del Sistema</h2>
          <div class="actions-bar">
            <input
              v-model="logsSearch"
              type="text"
              placeholder="Buscar en logs..."
              class="search-input"
            />
            <input
              v-model.number="logsLines"
              type="number"
              min="50"
              max="1000"
              step="50"
              class="form-input"
              style="width: 100px;"
              placeholder="Líneas"
            />
            <label class="logs-auto-refresh-toggle">
              <input type="checkbox" v-model="logAutoRefresh" @change="toggleLogAutoRefresh" />
              <span>Auto-refresh</span>
            </label>
            <button class="btn-secondary" @click="loadLogs">
              <span v-if="loadingLogs">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>

        <div class="logs-tabs">
          <button
            v-for="tab in [
              { id: 'celery', label: 'Celery Worker', icon: '⚙️' },
              { id: 'celery_task', label: 'Tarea Celery', icon: '📋' },
              { id: 'celery_realtime', label: 'Tareas en Tiempo Real', icon: '⚡' },
              { id: 'pm2', label: 'PM2', icon: '🔄' },
              { id: 'service', label: 'Servicio', icon: '🖥️' }
            ]"
            :key="tab.id"
            class="logs-tab"
            :class="{ active: logsTab === tab.id }"
            @click="logsTab = tab.id as any; onLogsTabChange()"
          >
            <span>{{ tab.icon }}</span>
            <span>{{ tab.label }}</span>
          </button>
        </div>

        <div class="logs-filters" v-if="logsTab === 'celery_task' || logsTab === 'pm2' || logsTab === 'service'">
          <div v-if="logsTab === 'celery_task'" class="filter-group">
            <label>Tarea Celery:</label>
            <select v-model="selectedLogTask" class="form-input" style="width: 300px;" @change="loadLogs()">
              <option value="">Seleccionar tarea...</option>
              <option v-for="task in celeryTasksList" :key="task.name" :value="task.name">
                {{ task.name }}
              </option>
            </select>
            <button class="btn-small btn-secondary" @click="loadCeleryTasksList" :disabled="loadingCeleryTasks">
              <span v-if="loadingCeleryTasks">⟳</span>
              <span v-else>↻</span>
              Actualizar Lista
            </button>
          </div>
          <div v-if="logsTab === 'pm2'" class="filter-group">
            <label>Proceso PM2:</label>
            <select v-model="selectedLogProcess" class="form-input" style="width: 250px;">
              <option value="">Todos los procesos</option>
              <option v-for="proc in pm2Processes" :key="proc.name" :value="proc.name">
                {{ proc.name }}
              </option>
            </select>
          </div>
          <div v-if="logsTab === 'service'" class="filter-group">
            <label>Servicio:</label>
            <select v-model="selectedLogService" class="form-input" style="width: 250px;">
              <option value="">Seleccionar servicio...</option>
              <option v-for="svc in systemdServices" :key="svc.name" :value="svc.name">
                {{ svc.name }}
              </option>
            </select>
          </div>
        </div>

        <!-- Vista de Tareas en Tiempo Real -->
        <div v-if="logsTab === 'celery_realtime'" class="realtime-tasks-container">
          <div class="realtime-header">
            <button class="btn-secondary" @click="loadActiveTasks" :disabled="loadingActiveTasks">
              <span v-if="loadingActiveTasks">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
            <label class="logs-auto-refresh-toggle">
              <input type="checkbox" v-model="logAutoRefresh" @change="toggleLogAutoRefresh" />
              <span>Auto-refresh (5s)</span>
            </label>
          </div>

          <div v-if="loadingActiveTasks" class="loading-state">
            <p>Cargando tareas activas...</p>
          </div>

          <div v-else class="realtime-tasks-content">
            <!-- Workers -->
            <div class="realtime-section">
              <h3>Workers Activos ({{ celeryActiveTasks.workers.length }})</h3>
              <div v-if="celeryActiveTasks.workers.length === 0" class="empty-state-small">
                <p>No hay workers activos</p>
              </div>
              <div v-else class="workers-list">
                <div v-for="worker in celeryActiveTasks.workers" :key="worker" class="worker-item">
                  <span class="worker-name">{{ worker }}</span>
                  <span class="worker-status active">● Activo</span>
                </div>
              </div>
            </div>

            <!-- Tareas Activas -->
            <div class="realtime-section">
              <h3>Tareas Activas ({{ celeryActiveTasks.active.length }})</h3>
              <div v-if="celeryActiveTasks.active.length === 0" class="empty-state-small">
                <p>No hay tareas ejecutándose actualmente</p>
              </div>
              <div v-else class="tasks-list">
                <div v-for="task in celeryActiveTasks.active" :key="task.task_id" class="task-item active">
                  <div class="task-header">
                    <span class="task-name">{{ task.task_name }}</span>
                    <span class="task-status active">● Ejecutando</span>
                  </div>
                  <div class="task-details">
                    <div><strong>ID:</strong> <code>{{ task.task_id }}</code></div>
                    <div><strong>Worker:</strong> {{ task.worker }}</div>
                    <div v-if="task.time_start"><strong>Iniciada:</strong> {{ formatTaskTime(task.time_start) }}</div>
                    <div v-if="task.args && task.args.length"><strong>Args:</strong> {{ JSON.stringify(task.args) }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Tareas Programadas -->
            <div class="realtime-section">
              <h3>Tareas Programadas ({{ celeryActiveTasks.scheduled.length }})</h3>
              <div v-if="celeryActiveTasks.scheduled.length === 0" class="empty-state-small">
                <p>No hay tareas programadas</p>
              </div>
              <div v-else class="tasks-list">
                <div v-for="task in celeryActiveTasks.scheduled" :key="task.task_id" class="task-item scheduled">
                  <div class="task-header">
                    <span class="task-name">{{ task.task_name }}</span>
                    <span class="task-status scheduled">⏰ Programada</span>
                  </div>
                  <div class="task-details">
                    <div><strong>ID:</strong> <code>{{ task.task_id }}</code></div>
                    <div><strong>Worker:</strong> {{ task.worker }}</div>
                    <div v-if="task.eta"><strong>ETA:</strong> {{ formatTaskTime(task.eta) }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Tareas Reservadas -->
            <div class="realtime-section">
              <h3>Tareas Reservadas ({{ celeryActiveTasks.reserved.length }})</h3>
              <div v-if="celeryActiveTasks.reserved.length === 0" class="empty-state-small">
                <p>No hay tareas reservadas</p>
              </div>
              <div v-else class="tasks-list">
                <div v-for="task in celeryActiveTasks.reserved" :key="task.task_id" class="task-item reserved">
                  <div class="task-header">
                    <span class="task-name">{{ task.task_name }}</span>
                    <span class="task-status reserved">⏳ En Cola</span>
                  </div>
                  <div class="task-details">
                    <div><strong>ID:</strong> <code>{{ task.task_id }}</code></div>
                    <div><strong>Worker:</strong> {{ task.worker }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Vista de Logs Normal -->
        <template v-else>
          <div v-if="loadingLogs" class="loading-state">
            <p>Cargando logs...</p>
          </div>

          <div v-else class="logs-container">
            <div class="logs-content">
              <pre class="logs-text" :class="{ 'filtered': logsSearch }">{{ filteredLogs }}</pre>
            </div>
            <div v-if="!logsContent" class="empty-state">
              <p>No hay logs disponibles. Selecciona un tipo de log y haz clic en "Actualizar".</p>
            </div>
          </div>
        </template>
      </section>

      <section v-if="activeSection === 'terminal'" class="section">
        <div class="section-header">
          <h2>Terminal SSH</h2>
          <div class="actions-bar">
            <label class="terminal-sudo-toggle">
              <input type="checkbox" v-model="terminalUseSudo" />
              <span>Usar sudo</span>
            </label>
            <button class="btn-secondary" @click="clearTerminal">
              🗑️ Limpiar
            </button>
          </div>
        </div>

        <div class="terminal-container">
          <div class="terminal-output" ref="terminalOutput">
            <div v-for="(entry, index) in terminalHistory" :key="index" class="terminal-entry">
              <div class="terminal-prompt">
                <span class="prompt-user">{{ terminalUser }}</span>
                <span class="prompt-separator">@</span>
                <span class="prompt-host">{{ terminalHost }}</span>
                <span class="prompt-separator">:</span>
                <span class="prompt-path">{{ terminalPath }}</span>
                <span class="prompt-separator">$</span>
                <span v-if="entry.use_sudo" class="prompt-sudo">sudo</span>
              </div>
              <div class="terminal-command">{{ entry.command }}</div>
              <div v-if="entry.output" class="terminal-output-text" :class="{ 'terminal-error': !entry.success }">
                {{ entry.output }}
              </div>
              <div v-if="entry.exit_status !== undefined" class="terminal-exit-status">
                [Exit code: {{ entry.exit_status }}]
              </div>
            </div>
            <div v-if="terminalExecuting" class="terminal-entry">
              <div class="terminal-prompt">
                <span class="prompt-user">{{ terminalUser }}</span>
                <span class="prompt-separator">@</span>
                <span class="prompt-host">{{ terminalHost }}</span>
                <span class="prompt-separator">:</span>
                <span class="prompt-path">{{ terminalPath }}</span>
                <span class="prompt-separator">$</span>
                <span v-if="terminalUseSudo" class="prompt-sudo">sudo</span>
              </div>
              <div class="terminal-command">{{ terminalCurrentCommand }}</div>
              <div class="terminal-executing">⏳ Ejecutando...</div>
            </div>
          </div>
          <div class="terminal-input-container">
            <input
              v-model="terminalCurrentCommand"
              @keyup.enter="executeTerminalCommand"
              @keyup.arrow-up="terminalHistoryUp"
              @keyup.arrow-down="terminalHistoryDown"
              type="text"
              class="terminal-input"
              placeholder="Escribe un comando y presiona Enter..."
              :disabled="terminalExecuting"
              ref="terminalInput"
            />
            <button 
              class="btn-primary terminal-send-btn" 
              @click="executeTerminalCommand"
              :disabled="terminalExecuting || !terminalCurrentCommand?.trim()"
            >
              ▶
            </button>
          </div>
        </div>
      </section>
    </main>

    <!-- Modal: Crear Servidor -->
    <div v-if="showCreateServer" class="modal-overlay" @click="showCreateServer = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Crear Nuevo Servidor</h2>
          <button class="modal-close" @click="showCreateServer = false">×</button>
        </div>
        <form @submit.prevent="createServer" class="modal-form">
          <div class="form-group">
            <label>Nombre del Servidor *</label>
            <input v-model="newServer.nombre" type="text" required class="form-input" placeholder="Ej: Servidor Principal" />
          </div>
          <div class="form-group">
            <label>Tipo de Servidor *</label>
            <select v-model="newServer.tipo_servidor" required class="form-input">
              <option value="">Seleccionar...</option>
              <option value="FIREBIRD">Firebird</option>
              <option value="POSTGRESQL">PostgreSQL</option>
              <option value="SQLSERVER">SQL Server</option>
              <option value="MYSQL">MySQL</option>
            </select>
          </div>
          <div class="form-group">
            <label>Host/IP *</label>
            <input v-model="newServer.host" type="text" required class="form-input" placeholder="192.168.1.100" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Puerto</label>
              <input v-model.number="newServer.puerto" type="number" class="form-input" placeholder="3050" />
            </div>
            <div class="form-group">
              <label>Usuario *</label>
              <input v-model="newServer.usuario" type="text" required class="form-input" placeholder="SYSDBA" />
            </div>
          </div>
          <div class="form-group">
            <label>Contraseña *</label>
            <input v-model="newServer.password" type="password" required class="form-input" placeholder="••••••••" />
          </div>
          <div class="form-group">
            <label>Ruta Maestra (Opcional)</label>
            <input v-model="newServer.ruta_maestra" type="text" class="form-input" placeholder="C:/Visual TNS/ADMIN.gdb" />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreateServer = false">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="creatingServer">
              <span v-if="creatingServer">⟳</span>
              <span v-else>Crear Servidor</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Crear VPN -->
    <div v-if="showCreateVpn" class="modal-overlay" @click="showCreateVpn = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Crear Nuevo Túnel VPN</h2>
          <button class="modal-close" @click="showCreateVpn = false">×</button>
        </div>
        <form @submit.prevent="createVpnConfig" class="modal-form">
          <div class="form-group">
            <label>Nombre del Cliente/PC *</label>
            <input v-model="newVpn.nombre" type="text" required class="form-input" placeholder="Ej: PC Oficina Principal" />
            <small>Nombre descriptivo para identificar este túnel</small>
          </div>
          <div class="form-group">
            <label>IP Deseada (Opcional)</label>
            <input v-model="newVpn.ip_address" type="text" class="form-input" placeholder="10.8.0.X" />
            <small>Dejar vacío para asignación automática</small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newVpn.activo" />
              Activar inmediatamente
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreateVpn = false">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="creatingVpn">
              <span v-if="creatingVpn">⟳</span>
              <span v-else>Crear Túnel</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Estadísticas Detalladas -->
    <div v-if="showStatsModal" class="modal-overlay" @click="showStatsModal = false">
      <div class="modal-content stats-modal" @click.stop>
        <div class="modal-header">
          <h2>Estadísticas Detalladas</h2>
          <button class="modal-close" @click="showStatsModal = false">×</button>
        </div>
        <div v-if="selectedStats" class="stats-content">
          <div class="stat-section">
            <h3>{{ selectedStats.nombre || 'Sin nombre' }}</h3>
            <p class="stat-ip"><code>{{ selectedStats.ip_address || '-' }}</code></p>
          </div>
          
          <div class="stat-section">
            <h4>Estado de Conexión</h4>
            <div class="stat-row">
              <span class="stat-label">Estado:</span>
              <span class="stat-value" :class="selectedStats.connected ? 'connected' : 'disconnected'">
                <span class="status-dot"></span>
                {{ selectedStats.connected ? 'Conectado' : 'Desconectado' }}
              </span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Último Handshake:</span>
              <span class="stat-value">
                {{ selectedStats.last_handshake_seconds_ago !== null ? formatHandshakeTime(selectedStats.last_handshake_seconds_ago) : 'Nunca' }}
              </span>
            </div>
            <div class="stat-row" v-if="selectedStats.endpoint">
              <span class="stat-label">Endpoint:</span>
              <span class="stat-value"><code>{{ selectedStats.endpoint }}</code></span>
            </div>
          </div>
          
          <div class="stat-section">
            <h4>Tráfico</h4>
            <div class="stat-row">
              <span class="stat-label">Enviado (↑):</span>
              <span class="stat-value">{{ formatBytes(selectedStats.tx_bytes || 0) }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Recibido (↓):</span>
              <span class="stat-value">{{ formatBytes(selectedStats.rx_bytes || 0) }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Total:</span>
              <span class="stat-value">{{ formatBytes(selectedStats.total_bytes || 0) }}</span>
            </div>
          </div>
          
          <div class="stat-section" v-if="selectedStats.persistent_keepalive">
            <div class="stat-row">
              <span class="stat-label">Keepalive:</span>
              <span class="stat-value">Cada {{ selectedStats.persistent_keepalive }} segundos</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Detalles del Servidor -->
    <div v-if="showServerDetailsModal" class="modal-overlay" @click="showServerDetailsModal = false">
      <div class="modal-content server-details-modal" @click.stop>
        <div class="modal-header">
          <h2>Detalles del Servidor</h2>
          <button class="modal-close" @click="showServerDetailsModal = false">×</button>
        </div>
        <div v-if="loadingServerDetails" class="loading-state">
          <p>Cargando detalles...</p>
        </div>
        <div v-else-if="selectedServer" class="server-details-content">
          <!-- Información del Servidor -->
          <div class="detail-section">
            <h3>Información General</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">Nombre:</span>
                <span class="detail-value">{{ selectedServer.nombre }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Tipo:</span>
                <span class="detail-value">
                  <span class="server-badge" :class="`badge-${selectedServer.tipo_servidor?.toLowerCase()}`">
                    {{ selectedServer.tipo_servidor }}
                  </span>
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Host/IP:</span>
                <span class="detail-value"><code>{{ selectedServer.host }}</code></span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Puerto:</span>
                <span class="detail-value">{{ selectedServer.puerto || 'Por defecto' }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Usuario:</span>
                <span class="detail-value">{{ selectedServer.usuario }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Estado:</span>
                <span class="detail-value">
                  <span class="status-badge" :class="selectedServer.activo ? 'status-active' : 'status-inactive'">
                    {{ selectedServer.activo ? 'Activo' : 'Inactivo' }}
                  </span>
                </span>
              </div>
              <div class="detail-item" v-if="(selectedServer as any).ruta_maestra">
                <span class="detail-label">Ruta Maestra:</span>
                <span class="detail-value"><code>{{ (selectedServer as any).ruta_maestra }}</code></span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Fecha Creación:</span>
                <span class="detail-value">{{ formatDate((selectedServer as any).fecha_creacion) }}</span>
              </div>
            </div>
          </div>

          <!-- Empresas Asociadas -->
          <div class="detail-section">
            <div class="section-header-inline">
              <h3>Empresas Asociadas</h3>
              <span class="badge-count">{{ serverEmpresas.length }} empresas</span>
            </div>
            <div v-if="serverEmpresas.length === 0" class="empty-state-small">
              <p>No hay empresas asociadas a este servidor</p>
            </div>
            <div v-else class="empresas-list">
              <table class="details-table">
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>NIT</th>
                    <th>Año Fiscal</th>
                    <th>Estado</th>
                    <th>Última Extracción</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="empresa in serverEmpresas" :key="empresa.id">
                    <td><strong>{{ empresa.nombre }}</strong></td>
                    <td><code>{{ empresa.nit || '-' }}</code></td>
                    <td>{{ empresa.anio_fiscal }}</td>
                    <td>
                      <span class="status-badge" :class="empresa.estado === 'ACTIVO' ? 'status-active' : 'status-inactive'">
                        {{ empresa.estado }}
                      </span>
                    </td>
                    <td>{{ empresa.ultima_extraccion ? formatDate(empresa.ultima_extraccion) : 'Nunca' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Acciones -->
          <div class="modal-actions">
            <button class="btn-secondary" @click="showServerDetailsModal = false">Cerrar</button>
            <button class="btn-primary" @click="scanEmpresas(selectedServer.id)" :disabled="scanningServer === selectedServer.id">
              <svg v-if="scanningServer === selectedServer.id" class="spinner-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              Escanear Empresas
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Logs del Servicio -->
    <div v-if="showLogsModal && selectedLogs" class="modal-overlay" @click="showLogsModal = false">
      <div class="modal-content logs-modal" @click.stop>
        <div class="modal-header">
          <h2>Logs: {{ selectedLogs.name }} ({{ selectedLogs.type }})</h2>
          <button class="modal-close" @click="showLogsModal = false">×</button>
        </div>
        <div class="logs-content">
          <pre class="logs-text">{{ selectedLogs.logs }}</pre>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showLogsModal = false">Cerrar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, computed } from 'vue'

definePageMeta({
  layout: false,
  middleware: 'auth'
})

interface Servidor {
  id: number
  nombre: string
  tipo_servidor: string
  host: string
  puerto?: number
  usuario: string
  activo?: boolean
  ruta_maestra?: string
  fecha_creacion?: string
}

interface Empresa {
  id: number
  nombre: string
  nit: string
  anio_fiscal: number
  codigo: string
  servidor_nombre?: string
  servidor?: number
}

const session = useSessionStore()
const api = useApiClient()
const activeSection = ref('servidores')
const empresaSearch = ref('')
const empresaFilterServidor = ref('')
const empresaFilterEstado = ref('')
const empresaSortField = ref<string>('nombre')
const empresaSortOrder = ref<'asc' | 'desc'>('asc')
const empresaCurrentPage = ref(1)
const empresaPageSize = ref(10)

const user = computed(() => session.user)

// Secciones ordenadas de forma secuencial según el flujo del sistema
const sections = [
  { 
    id: 'servidores', 
    name: '1. Servidores', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
      <line x1="8" y1="21" x2="16" y2="21"/>
      <line x1="12" y1="17" x2="12" y2="21"/>
    </svg>`
  },
  { 
    id: 'vpn', 
    name: '2. VPN', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      <path d="M9 12l2 2 4-4"/>
    </svg>`
  },
  { 
    id: 'empresas', 
    name: '3. Empresas', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
      <circle cx="9" cy="7" r="4"/>
      <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>`
  },
  { 
    id: 'usuarios', 
    name: '3.5. Usuarios', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>`
  },
  { 
    id: 'api-keys', 
    name: '4. API Keys', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
    </svg>`
  },
  { 
    id: 'ml', 
    name: '5. ML Models', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
      <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
    </svg>`
  },
  { 
    id: 'scrapers', 
    name: 'Scrapers', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>`
  },
  { 
    id: 'servicios', 
    name: 'Servicios', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
      <line x1="8" y1="21" x2="16" y2="21"/>
      <line x1="12" y1="17" x2="12" y2="21"/>
    </svg>`
  },
  { 
    id: 'logs', 
    name: 'Logs', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
      <polyline points="10 9 9 9 8 9"/>
    </svg>`
  },
  { 
    id: 'terminal', 
    name: 'Terminal', 
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="4 7 10 7 14 17 20 17"/>
      <line x1="21" y1="12" x2="3" y2="12"/>
    </svg>`
  },
]

const servers = ref<Servidor[]>([])
const empresas = ref<Empresa[]>([])
const mlModels = ref<any[]>([])
const mlFilterEmpresa = ref('')
const newModelEmpresaId = ref('')
const trainingModel = ref<number | null>(null)
const loadingML = ref(false)
const vpnConfigs = ref<any[]>([])
const apiKeys = ref<any[]>([])
const loadingServers = ref(false)
const loadingEmpresas = ref(false)
const loadingVpn = ref(false)
const loadingApiKeys = ref(false)
const scanningServer = ref<number | null>(null)
const activeScanTasks = ref<Record<number, string>>({}) // servidor_id -> task_id
const showCreateServer = ref(false)
const showEditServer = ref(false)
const editingServer = ref<Servidor | null>(null)
const showCreateVpn = ref(false)
const showCreateApiKey = ref(false)
const creatingServer = ref(false)
const creatingVpn = ref(false)
const creatingApiKey = ref(false)
const showExtractDataModal = ref(false)
const extractingData = ref(false)
const selectedEmpresaForExtract = ref<Empresa | null>(null)
const extractDateRange = ref({ fecha_inicio: '', fecha_fin: '' })
const editingNameId = ref<number | null>(null)
const editingNameValue = ref('')
const nameInput = ref<any>(null)
const showStatsModal = ref(false)
const selectedStats = ref<any>(null)
const syncingPeers = ref(false)
const showServerDetailsModal = ref(false)
const selectedServer = ref<Servidor | null>(null)
const serverEmpresas = ref<any[]>([])
const loadingServerDetails = ref(false)
const serviceTab = ref<'systemd' | 'pm2'>('systemd')
const systemdServices = ref<any[]>([])
const pm2Processes = ref<any[]>([])
const loadingSystemd = ref(false)
const loadingPm2 = ref(false)
const loadingSystemInfo = ref(false)
const systemInfo = ref<any>(null)
const showLogsModal = ref(false)
const selectedLogs = ref<{name: string, logs: string, type: string} | null>(null)
const terminalHistory = ref<Array<{command: string, output: string, exit_status: number, success: boolean, use_sudo: boolean}>>([])
const terminalCurrentCommand = ref('')
const terminalExecuting = ref(false)
const terminalUseSudo = ref(false)
const terminalHistoryIndex = ref(-1)
const terminalUser = ref('root')
const terminalHost = ref('servidor')
const terminalPath = ref('~')
const terminalOutput = ref<HTMLElement | null>(null)
const terminalInput = ref<HTMLInputElement | null>(null)

// Logs section
const logsTab = ref<'celery' | 'celery_task' | 'celery_realtime' | 'pm2' | 'service'>('celery')
const logsContent = ref('')
const loadingLogs = ref(false)
const logsLines = ref(200)
const logsSearch = ref('')
const selectedLogService = ref('')
const selectedLogTask = ref('descubrir_empresas')
const selectedLogProcess = ref('')
const logAutoRefresh = ref(false)
const logRefreshInterval = ref<NodeJS.Timeout | null>(null)
const celeryTasksList = ref<Array<{name: string, routing_key?: string, queue?: string}>>([])
const loadingCeleryTasks = ref(false)
const celeryActiveTasks = ref<any>({
  active: [],
  scheduled: [],
  reserved: [],
  workers: [],
  stats: {}
})
const loadingActiveTasks = ref(false)

const newServer = ref({
  nombre: '',
  tipo_servidor: '',
  host: '',
  puerto: 0,
  usuario: '',
  password: '',
  ruta_maestra: ''
})

const newVpn = ref({
  nombre: '',
  ip_address: '',
  activo: true
})

const sortedAndFilteredEmpresas = computed(() => {
  let result = [...empresas.value]
  
  // Aplicar búsqueda por texto
  if (empresaSearch.value) {
    const search = empresaSearch.value.toLowerCase()
    result = result.filter(e => 
      e.nombre.toLowerCase().includes(search) ||
      (e.nit || '').toLowerCase().includes(search) ||
      (e.codigo || '').toLowerCase().includes(search)
    )
  }
  
  // Aplicar filtro por servidor
  if (empresaFilterServidor.value) {
    result = result.filter(e => e.servidor === Number(empresaFilterServidor.value))
  }
  
  // Aplicar filtro por estado
  if (empresaFilterEstado.value) {
    result = result.filter(e => (e.estado || 'ACTIVO') === empresaFilterEstado.value)
  }
  
  // Aplicar ordenamiento
  result.sort((a, b) => {
    let aVal: any = a[empresaSortField.value]
    let bVal: any = b[empresaSortField.value]
    
    // Manejar valores nulos/undefined
    if (aVal == null) aVal = ''
    if (bVal == null) bVal = ''
    
    // Convertir a string para comparación
    aVal = String(aVal).toLowerCase()
    bVal = String(bVal).toLowerCase()
    
    if (empresaSortOrder.value === 'asc') {
      return aVal < bVal ? -1 : aVal > bVal ? 1 : 0
    } else {
      return aVal > bVal ? -1 : aVal < bVal ? 1 : 0
    }
  })
  
  return result
})

const empresaTotalPages = computed(() => {
  return Math.ceil(sortedAndFilteredEmpresas.value.length / empresaPageSize.value)
})

const paginatedEmpresas = computed(() => {
  const start = (empresaCurrentPage.value - 1) * empresaPageSize.value
  const end = start + empresaPageSize.value
  return sortedAndFilteredEmpresas.value.slice(start, end)
})

const sortEmpresas = (field: string) => {
  if (empresaSortField.value === field) {
    // Cambiar orden si es el mismo campo
    empresaSortOrder.value = empresaSortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    // Nuevo campo, orden ascendente por defecto
    empresaSortField.value = field
    empresaSortOrder.value = 'asc'
  }
  // Resetear a primera página al cambiar ordenamiento
  empresaCurrentPage.value = 1
}

const loadServers = async () => {
  loadingServers.value = true
  try {
    const response = await api.get<Servidor[]>('/api/servidores/')
    servers.value = Array.isArray(response) ? response : (response as any).results || []
    
    // Verificar si hay procesos corriendo para cada servidor
    for (const server of servers.value) {
      if (activeScanTasks.value[server.id]) {
        const taskId = activeScanTasks.value[server.id]
        try {
          const statusResponse = await api.get(`/api/sistema/estado-descubrimiento/?task_id=${taskId}`)
          const status = statusResponse.status
          
          // Si el proceso ya terminó, limpiar
          if (status === 'SUCCESS' || status === 'ERROR' || status === 'FAILED') {
            delete activeScanTasks.value[server.id]
          }
        } catch (error) {
          // Si hay error consultando, asumir que terminó
          delete activeScanTasks.value[server.id]
        }
      }
    }
  } catch (error) {
    console.error('Error cargando servidores:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Error al cargar servidores',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: {
        container: 'swal-z-index-fix'
      }
    })
  } finally {
    loadingServers.value = false
  }
}

const loadEmpresas = async () => {
  loadingEmpresas.value = true
  try {
    const response = await api.get<any>('/api/empresas-servidor/')
    const data = Array.isArray(response) ? response : (response as any).results || []
    empresas.value = data.map((e: any) => {
      // El backend puede devolver servidor_nombre directamente o como objeto servidor
      let servidorNombre = '-'
      let servidorId = null
      
      if (e.servidor_nombre) {
        // Si viene directamente del serializer
        servidorNombre = e.servidor_nombre
      } else if (e.servidor) {
        // Si viene como objeto
        if (typeof e.servidor === 'object') {
          servidorNombre = e.servidor.nombre || '-'
          servidorId = e.servidor.id
        } else {
          // Si es solo un ID, necesitamos buscarlo en la lista de servidores
          servidorId = e.servidor
          const server = servers.value.find(s => s.id === servidorId)
          if (server) {
            servidorNombre = server.nombre
          }
        }
      }
      
      return {
        id: e.id,
        nombre: e.nombre,
        nit: e.nit || '',
        anio_fiscal: e.anio_fiscal,
        codigo: e.codigo || '',
        servidor_nombre: servidorNombre,
        servidor: servidorId || (typeof e.servidor === 'object' ? e.servidor.id : e.servidor),
        estado: e.estado || 'ACTIVO'
      }
    })
  } catch (error) {
    console.error('Error cargando empresas:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Error al cargar empresas',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: {
        container: 'swal-z-index-fix'
      }
    })
  } finally {
    loadingEmpresas.value = false
  }
}

const scanEmpresas = async (serverId: number) => {
  // Verificar si ya hay un proceso corriendo
  if (activeScanTasks.value[serverId]) {
    const Swal = (await import('sweetalert2')).default
    const taskId = activeScanTasks.value[serverId]
    
    // Consultar estado del proceso existente
    try {
      const statusResponse = await api.get(`/api/sistema/estado-descubrimiento/?task_id=${taskId}`)
      const status = statusResponse.status
      const meta = statusResponse.meta || {}
      
      if (status === 'PROCESSING' || status === 'PENDING') {
        await Swal.fire({
          title: 'Proceso en curso',
          html: `
            <div style="text-align: left;">
              <p><strong>Servidor:</strong> ${meta.servidor_nombre || 'Desconocido'}</p>
              <p><strong>Estado:</strong> ${meta.status || 'Procesando...'}</p>
              <p><strong>Empresas encontradas hasta ahora:</strong> ${meta.empresas_encontradas || 0}</p>
            </div>
          `,
          icon: 'info',
          confirmButtonText: 'Cerrar',
          customClass: {
            container: 'swal-z-index-fix'
          }
        })
        return
      } else if (status === 'SUCCESS') {
        // Proceso completado, limpiar y continuar
        delete activeScanTasks.value[serverId]
      }
    } catch (error) {
      console.error('Error consultando estado:', error)
    }
  }
  
  scanningServer.value = serverId
  const Swal = (await import('sweetalert2')).default
  
  try {
    // Iniciar proceso asíncrono
    const response = await api.post('/api/sistema/descubrir_empresas/', { servidor_id: serverId })
    const taskId = response.task_id
    
    if (!taskId) {
      throw new Error('No se recibió task_id del servidor')
    }
    
    // Guardar task_id activo
    activeScanTasks.value[serverId] = taskId
    
    // Mostrar modal de progreso
    const server = servers.value.find(s => s.id === serverId)
    const serverName = server?.nombre || 'Servidor'
    
    Swal.fire({
      title: 'Escaneando empresas...',
      html: `
        <div style="text-align: left;">
          <p><strong>Servidor:</strong> ${serverName}</p>
          <p id="scan-status">Conectando al servidor...</p>
          <div style="margin-top: 15px;">
            <div class="progress-bar" style="width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden;">
              <div id="scan-progress" style="width: 0%; height: 100%; background: linear-gradient(90deg, #4CAF50, #45a049); transition: width 0.3s;"></div>
            </div>
          </div>
          <p id="scan-details" style="margin-top: 10px; font-size: 0.9em; color: #666;"></p>
        </div>
      `,
      icon: 'info',
      allowOutsideClick: false,
      showConfirmButton: false,
      didOpen: () => {
        Swal.showLoading()
      },
      customClass: {
        container: 'swal-z-index-fix'
      }
    })
    
    // Polling para ver el progreso
    const pollInterval = setInterval(async () => {
      try {
        const statusResponse = await api.get(`/api/sistema/estado-descubrimiento/?task_id=${taskId}`)
        const status = statusResponse.status
        const meta = statusResponse.meta || {}
        const result = statusResponse.result
        
        const statusElement = document.getElementById('scan-status')
        const progressElement = document.getElementById('scan-progress')
        const detailsElement = document.getElementById('scan-details')
        
        if (status === 'PROCESSING' || status === 'PENDING') {
          if (statusElement) {
            statusElement.textContent = meta.status || 'Procesando...'
          }
          if (detailsElement) {
            detailsElement.textContent = `Empresas encontradas: ${meta.empresas_encontradas || 0}`
          }
          // Progreso aproximado (no tenemos porcentaje exacto, así que animamos)
          if (progressElement) {
            const currentWidth = parseInt(progressElement.style.width) || 0
            if (currentWidth < 90) {
              progressElement.style.width = `${Math.min(currentWidth + 5, 90)}%`
            }
          }
        } else if (status === 'SUCCESS' && result) {
          clearInterval(pollInterval)
          delete activeScanTasks.value[serverId]
          scanningServer.value = null
          
          await Swal.fire({
            title: '¡Escaneo completado!',
            html: `
              <div style="text-align: left;">
                <p><strong>Servidor:</strong> ${result.servidor_nombre || serverName}</p>
                <p><strong>Total de empresas encontradas:</strong> <strong style="color: #4CAF50;">${result.total_empresas || 0}</strong></p>
                <p style="margin-top: 10px; color: #666;">${result.mensaje || 'El escaneo se completó exitosamente.'}</p>
              </div>
            `,
            icon: 'success',
            confirmButtonText: 'Aceptar',
            customClass: {
              container: 'swal-z-index-fix'
            }
          })
          
          // Recargar empresas
          await loadEmpresas()
        } else if (status === 'ERROR' || status === 'FAILED') {
          clearInterval(pollInterval)
          delete activeScanTasks.value[serverId]
          scanningServer.value = null
          
          await Swal.fire({
            title: 'Error en el escaneo',
            html: `
              <div style="text-align: left;">
                <p><strong>Error:</strong></p>
                <p style="color: #d32f2f;">${statusResponse.error || 'Error desconocido'}</p>
              </div>
            `,
            icon: 'error',
            confirmButtonText: 'Aceptar',
            customClass: {
              container: 'swal-z-index-fix'
            }
          })
        }
      } catch (error: any) {
        console.error('Error consultando progreso:', error)
        // Continuar polling aunque haya error
      }
    }, 2000) // Polling cada 2 segundos
    
    // Timeout de seguridad (5 minutos)
    setTimeout(() => {
      clearInterval(pollInterval)
      if (activeScanTasks.value[serverId]) {
        delete activeScanTasks.value[serverId]
        scanningServer.value = null
        Swal.close()
        Swal.fire({
          title: 'Tiempo de espera agotado',
          text: 'El proceso está tomando más tiempo del esperado. Puede que aún esté ejecutándose en segundo plano.',
          icon: 'warning',
          confirmButtonText: 'Aceptar',
          customClass: {
            container: 'swal-z-index-fix'
          }
        })
      }
    }, 300000) // 5 minutos
    
  } catch (error: any) {
    console.error('Error escaneando empresas:', error)
    scanningServer.value = null
    
    await Swal.fire({
      title: 'Error al iniciar escaneo',
      html: `
        <div style="text-align: left;">
          <p style="color: #d32f2f;">${error?.data?.error || error?.message || 'Error desconocido al iniciar el escaneo'}</p>
        </div>
      `,
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: {
        container: 'swal-z-index-fix'
      }
    })
  }
}

const navigateToScraper = (path: string) => {
  // TODO: Navegar a la página del scraper
  console.log('Navegar a:', path)
}

const createServer = async () => {
  creatingServer.value = true
  try {
    await api.post('/api/servidores/', newServer.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Éxito!',
      text: 'Servidor creado exitosamente',
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: {
        container: 'swal-z-index-fix'
      }
    })
    showCreateServer.value = false
    newServer.value = {
      nombre: '',
      tipo_servidor: '',
      host: '',
      puerto: 0,
      usuario: '',
      password: '',
      ruta_maestra: ''
    }
    await loadServers()
  } catch (error: any) {
    console.error('Error creando servidor:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al crear servidor',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: {
        container: 'swal-z-index-fix'
      }
    })
  } finally {
    creatingServer.value = false
  }
}

const loadVpnConfigs = async () => {
  loadingVpn.value = true
  try {
    const response = await api.get<any>('/api/vpn/configs/')
    const configs = Array.isArray(response) ? response : (response as any).results || []
    
    // Cargar estadísticas de tráfico para cada configuración
    try {
      const statsResponse = await api.get<any>('/api/vpn/configs/peer-stats/')
      const peerStats = statsResponse.peers || []
      
      // Combinar configuraciones con estadísticas
      vpnConfigs.value = configs.map((config: any) => {
        const stats = peerStats.find((p: any) => p.id === config.id || p.public_key === config.public_key)
        return {
          ...config,
          stats: stats || null
        }
      })
    } catch (statsError) {
      console.warn('Error cargando estadísticas:', statsError)
      vpnConfigs.value = configs
    }
  } catch (error) {
    console.error('Error cargando configuraciones VPN:', error)
    alert('Error al cargar configuraciones VPN')
  } finally {
    loadingVpn.value = false
  }
}

const createVpnConfig = async () => {
  creatingVpn.value = true
  try {
    await api.post('/api/vpn/configs/', newVpn.value)
    alert('Túnel VPN creado exitosamente')
    showCreateVpn.value = false
    newVpn.value = {
      nombre: '',
      ip_address: '',
      activo: true
    }
    await loadVpnConfigs()
  } catch (error: any) {
    console.error('Error creando túnel VPN:', error)
    alert(error?.data?.error || error?.message || 'Error al crear túnel VPN')
  } finally {
    creatingVpn.value = false
  }
}

const readVpnConfig = async (configId: number) => {
  try {
    const response = await api.get(`/api/vpn/configs/${configId}/read-config/`)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Configuración Actual',
      html: `
        <div style="text-align: left;">
          <p><strong>Ruta del archivo:</strong> ${response.config_file_path || 'No guardado'}</p>
          <p><strong>Tiene clave privada:</strong> ${response.has_private_key ? 'Sí' : 'No'}</p>
          <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px; max-height: 400px; overflow-y: auto;">
            <pre style="white-space: pre-wrap; word-wrap: break-word; font-size: 0.85em; margin: 0;">${response.config_content || 'No hay contenido'}</pre>
          </div>
        </div>
      `,
      width: '80%',
      icon: 'info',
      confirmButtonText: 'Cerrar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } catch (error: any) {
    console.error('Error leyendo configuración VPN:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al leer configuración VPN',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const downloadVpnConfig = async (configId: number) => {
  try {
    // El backend ahora SIEMPRE regenera el config con la clave pública correcta
    const response = await api.get(`/api/vpn/configs/${configId}/download/`, {
      responseType: 'blob'
    })
    const blob = new Blob([response], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const config = vpnConfigs.value.find(c => c.id === configId)
    const filename = config ? `wg-${config.nombre.replace(/\s+/g, '_')}.conf` : `wg-${configId}.conf`
    a.download = filename
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Descargado',
      text: 'Archivo .conf descargado exitosamente (regenerado con clave pública actualizada)',
      icon: 'success',
      timer: 2000,
      showConfirmButton: false,
      customClass: { container: 'swal-z-index-fix' }
    })
  } catch (error: any) {
    console.error('Error descargando configuración VPN:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al descargar configuración VPN',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const deleteVpnConfigFile = async (configId: number) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar archivo .conf?',
    text: 'Esto eliminará el archivo pero mantendrá el registro. Puedes regenerarlo descargándolo nuevamente.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      const response = await api.post(`/api/vpn/configs/${configId}/delete-config/`)
      await Swal.fire({
        title: 'Eliminado',
        text: response.message || 'Archivo eliminado exitosamente',
        icon: 'success',
        timer: 1500,
        showConfirmButton: false,
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadVpnConfigs()
    } catch (error: any) {
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar archivo',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

const toggleVpnConfig = async (configId: number, activo: boolean) => {
  try {
    await api.patch(`/api/vpn/configs/${configId}/`, { activo })
    await loadVpnConfigs()
  } catch (error: any) {
    console.error('Error actualizando configuración VPN:', error)
    alert('Error al actualizar configuración VPN')
  }
}

const deleteVpnConfig = async (configId: number) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar configuración VPN?',
    text: 'Esto eliminará el registro completo, incluyendo el archivo .conf. Esta acción no se puede deshacer.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#d32f2f',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.delete(`/api/vpn/configs/${configId}/`)
      await Swal.fire({
        title: 'Eliminado',
        text: 'Configuración VPN eliminada exitosamente',
        icon: 'success',
        timer: 1500,
        showConfirmButton: false,
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadVpnConfigs()
    } catch (error: any) {
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar configuración VPN',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

const formatDate = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatBytes = (bytes: number): string => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const formatHandshakeTime = (secondsAgo: number): string => {
  if (secondsAgo === null || secondsAgo === undefined) return 'Nunca'
  if (secondsAgo < 60) return `Hace ${secondsAgo}s`
  if (secondsAgo < 3600) return `Hace ${Math.floor(secondsAgo / 60)}m`
  if (secondsAgo < 86400) return `Hace ${Math.floor(secondsAgo / 3600)}h`
  return `Hace ${Math.floor(secondsAgo / 86400)}d`
}

const startEditName = (id: number, currentName: string) => {
  editingNameId.value = id
  editingNameValue.value = currentName
  // Usar setTimeout para asegurar que el DOM se actualice
  setTimeout(() => {
    const input = document.querySelector('.inline-input') as HTMLInputElement
    if (input) {
      input.focus()
      input.select()
    }
  }, 10)
}

const saveName = async (id: number) => {
  if (!editingNameValue.value.trim()) {
    cancelEditName()
    return
  }
  
  try {
    await api.patch(`/api/vpn/configs/${id}/`, { nombre: editingNameValue.value.trim() })
    await loadVpnConfigs()
    editingNameId.value = null
    editingNameValue.value = ''
  } catch (error: any) {
    console.error('Error actualizando nombre:', error)
    alert('Error al actualizar nombre')
  }
}

const cancelEditName = () => {
  editingNameId.value = null
  editingNameValue.value = ''
}

const viewStats = async (id: number) => {
  try {
    const response = await api.get(`/api/vpn/configs/${id}/stats/`)
    selectedStats.value = response
    showStatsModal.value = true
  } catch (error: any) {
    console.error('Error cargando estadísticas:', error)
    alert('Error al cargar estadísticas')
  }
}

const syncPeers = async () => {
  syncingPeers.value = true
  try {
    const response = await api.post('/api/vpn/configs/sync-peers/')
    const created = response.created || 0
    const existing = response.existing || 0
    alert(`Sincronización completada:\n- ${created} nuevos peers importados\n- ${existing} peers ya existentes`)
    await loadVpnConfigs()
  } catch (error: any) {
    console.error('Error sincronizando peers:', error)
    alert(error?.data?.error || error?.message || 'Error al sincronizar peers')
  } finally {
    syncingPeers.value = false
  }
}

const viewEmpresaDetails = async (empresaId: number) => {
  const empresa = empresas.value.find(e => e.id === empresaId)
  if (!empresa) return
  
  const Swal = (await import('sweetalert2')).default
  await Swal.fire({
    title: 'Detalles de Empresa',
    html: `
      <div style="text-align: left;">
        <p><strong>Nombre:</strong> ${empresa.nombre}</p>
        <p><strong>NIT:</strong> ${empresa.nit}</p>
        <p><strong>Año Fiscal:</strong> ${empresa.anio_fiscal}</p>
        <p><strong>Código:</strong> ${empresa.codigo}</p>
        <p><strong>Servidor:</strong> ${empresa.servidor_nombre || '-'}</p>
        <p><strong>Estado:</strong> ${empresa.estado || 'ACTIVO'}</p>
      </div>
    `,
    icon: 'info',
    confirmButtonText: 'Cerrar',
    customClass: { container: 'swal-z-index-fix' }
  })
}

const viewServerDetails = async (serverId: number) => {
  loadingServerDetails.value = true
  try {
    // Obtener información completa del servidor
    const server = await api.get<Servidor>(`/api/servidores/${serverId}/`)
    selectedServer.value = server
    
    // Obtener empresas asociadas a este servidor
    const empresasResponse = await api.get<any>(`/api/empresas-servidor/?servidor=${serverId}`)
    const empresasData = Array.isArray(empresasResponse) ? empresasResponse : (empresasResponse as any).results || []
    serverEmpresas.value = empresasData
    
    showServerDetailsModal.value = true
  } catch (error: any) {
    console.error('Error cargando detalles del servidor:', error)
    alert('Error al cargar detalles del servidor')
  } finally {
    loadingServerDetails.value = false
  }
}

const handleLogout = () => {
  session.logout()
  navigateTo('/admin/login')
}

const loadSystemdServices = async () => {
  loadingSystemd.value = true
  try {
    const response = await api.get('/api/server/systemd_services/')
    systemdServices.value = response.services || []
  } catch (error: any) {
    console.error('Error cargando servicios systemd:', error)
    alert(error?.data?.error || 'Error al cargar servicios systemd')
    systemdServices.value = []
  } finally {
    loadingSystemd.value = false
  }
}

const loadPm2Processes = async () => {
  loadingPm2.value = true
  try {
    const response = await api.get('/api/server/pm2_processes/')
    pm2Processes.value = response.processes || []
  } catch (error: any) {
    console.error('Error cargando procesos PM2:', error)
    // PM2 puede no estar instalado, no es crítico
    pm2Processes.value = []
  } finally {
    loadingPm2.value = false
  }
}

const loadSystemInfo = async () => {
  loadingSystemInfo.value = true
  try {
    const response = await api.get('/api/server/system_info/')
    systemInfo.value = response
  } catch (error: any) {
    console.error('Error cargando información del sistema:', error)
    systemInfo.value = null
  } finally {
    loadingSystemInfo.value = false
  }
}

// Logs functions
const loadLogs = async () => {
  loadingLogs.value = true
  try {
    let response: any
    
    switch (logsTab.value) {
      case 'celery':
        response = await api.get(`/api/server/celery_logs/?lines=${logsLines.value}`)
        break
      case 'celery_task':
        if (!selectedLogTask.value) {
          alert('Por favor selecciona una tarea')
          return
        }
        response = await api.get(`/api/server/celery_task_logs/?task_name=${selectedLogTask.value}&lines=${logsLines.value}`)
        break
      case 'pm2':
        const pm2Params = selectedLogProcess.value 
          ? `process_name=${selectedLogProcess.value}&` 
          : ''
        response = await api.get(`/api/server/pm2_logs/?${pm2Params}lines=${logsLines.value}`)
        break
      case 'service':
        if (!selectedLogService.value) {
          alert('Por favor selecciona un servicio')
          return
        }
        response = await api.get(`/api/server/service_logs/?service_name=${selectedLogService.value}&service_type=systemd&lines=${logsLines.value}`)
        break
    }
    
    logsContent.value = response.logs || 'No hay logs disponibles'
    
    // Auto-scroll al final
    setTimeout(() => {
      const logsElement = document.querySelector('.logs-text')
      if (logsElement) {
        logsElement.scrollTop = logsElement.scrollHeight
      }
    }, 100)
  } catch (error: any) {
    console.error('Error cargando logs:', error)
    logsContent.value = `Error al cargar logs: ${error?.data?.error || error.message || 'Error desconocido'}`
  } finally {
    loadingLogs.value = false
  }
}

const onLogsTabChange = () => {
  if (logsTab.value === 'celery_realtime') {
    loadActiveTasks()
    loadCeleryTasksList()
  } else if (logsTab.value === 'celery_task') {
    loadCeleryTasksList()
  } else {
    loadLogs()
  }
}

const loadCeleryTasksList = async () => {
  loadingCeleryTasks.value = true
  try {
    const response = await api.get('/api/server/celery_tasks_list/')
    celeryTasksList.value = response.tasks || []
    
    // Si no hay tarea seleccionada y hay tareas disponibles, seleccionar la primera
    if (!selectedLogTask.value && celeryTasksList.value.length > 0) {
      selectedLogTask.value = celeryTasksList.value[0].name
    }
  } catch (error: any) {
    console.error('Error cargando lista de tareas Celery:', error)
    alert(error?.data?.error || 'Error al cargar lista de tareas')
  } finally {
    loadingCeleryTasks.value = false
  }
}

const loadActiveTasks = async () => {
  loadingActiveTasks.value = true
  try {
    const response = await api.get('/api/server/celery_active_tasks/')
    celeryActiveTasks.value = {
      active: response.active || [],
      scheduled: response.scheduled || [],
      reserved: response.reserved || [],
      workers: response.workers || [],
      stats: response.stats || {}
    }
  } catch (error: any) {
    console.error('Error cargando tareas activas:', error)
    celeryActiveTasks.value = {
      active: [],
      scheduled: [],
      reserved: [],
      workers: [],
      stats: {}
    }
  } finally {
    loadingActiveTasks.value = false
  }
}

const formatTaskTime = (timestamp: number | string | null) => {
  if (!timestamp) return '-'
  
  try {
    let date: Date
    
    // Celery puede devolver timestamps en segundos o como string ISO
    if (typeof timestamp === 'string') {
      date = new Date(timestamp)
    } else {
      // Si es un número, puede ser en segundos o milisegundos
      // Si es menor que un timestamp razonable en milisegundos, asumimos segundos
      if (timestamp < 10000000000) {
        date = new Date(timestamp * 1000)
      } else {
        date = new Date(timestamp)
      }
    }
    
    if (isNaN(date.getTime())) return '-'
    
    return date.toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch (e) {
    return String(timestamp)
  }
}

const toggleLogAutoRefresh = () => {
  if (logAutoRefresh.value) {
    // Iniciar auto-refresh cada 5 segundos
    logRefreshInterval.value = setInterval(() => {
      if (logsTab.value === 'celery_realtime') {
        loadActiveTasks()
      } else {
        loadLogs()
      }
    }, 5000)
  } else {
    // Detener auto-refresh
    if (logRefreshInterval.value) {
      clearInterval(logRefreshInterval.value)
      logRefreshInterval.value = null
    }
  }
}

const filteredLogs = computed(() => {
  if (!logsSearch.value || !logsContent.value) {
    return logsContent.value
  }
  
  const searchLower = logsSearch.value.toLowerCase()
  const lines = logsContent.value.split('\n')
  const filtered = lines.filter(line => line.toLowerCase().includes(searchLower))
  
  return filtered.length > 0 
    ? filtered.join('\n')
    : `No se encontraron líneas que coincidan con "${logsSearch.value}"`
})

const systemdAction = async (serviceName: string, action: string) => {
  if (!confirm(`¿Estás seguro de ${action} el servicio ${serviceName}?`)) return
  
  try {
    const response = await api.post('/api/server/systemd_action/', {
      service_name: serviceName,
      action: action
    })
    
    if (response.success) {
      alert(`Servicio ${serviceName} ${action} exitosamente`)
      await loadSystemdServices()
    } else {
      alert(`Error: ${response.message || response.stderr}`)
    }
  } catch (error: any) {
    console.error('Error ejecutando acción systemd:', error)
    alert(error?.data?.error || `Error al ${action} el servicio`)
  }
}

const pm2Action = async (processName: string, action: string) => {
  if (!confirm(`¿Estás seguro de ${action} el proceso ${processName}?`)) return
  
  try {
    const response = await api.post('/api/server/pm2_action/', {
      process_name: processName,
      action: action
    })
    
    if (response.success) {
      alert(`Proceso ${processName} ${action} exitosamente`)
      await loadPm2Processes()
    } else {
      alert(`Error: ${response.message || response.stderr}`)
    }
  } catch (error: any) {
    console.error('Error ejecutando acción PM2:', error)
    alert(error?.data?.error || `Error al ${action} el proceso`)
  }
}

const viewServiceLogs = async (serviceName: string, serviceType: string) => {
  try {
    const response = await api.get(`/api/server/service_logs/?service_name=${serviceName}&service_type=${serviceType}&lines=200`)
    selectedLogs.value = {
      name: serviceName,
      logs: response.logs || 'No hay logs disponibles',
      type: serviceType
    }
    showLogsModal.value = true
  } catch (error: any) {
    console.error('Error obteniendo logs:', error)
    alert(error?.data?.error || 'Error al obtener logs')
  }
}

const formatUptime = (seconds: number) => {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

// Watch para cargar servicios cuando se cambia a esa pestaña
watch(activeSection, (newSection) => {
  if (newSection === 'servicios') {
    // Cargar servicios automáticamente al cambiar a esta pestaña
    loadSystemInfo()
    loadSystemdServices()
    loadPm2Processes()
  } else if (newSection === 'logs') {
    // Cargar datos necesarios para logs
    loadSystemdServices()
    loadPm2Processes()
    loadCeleryTasksList()
  } else if (newSection === 'terminal') {
    // Enfocar el input del terminal cuando se cambia a esa pestaña
    setTimeout(() => {
      if (terminalInput.value) {
        terminalInput.value.focus()
      }
    }, 100)
  }
})

const executeTerminalCommand = async () => {
  const command = terminalCurrentCommand.value.trim()
  if (!command || terminalExecuting.value) return
  
  terminalExecuting.value = true
  const commandToExecute = command
  
  try {
    const response = await api.post('/api/server/execute_command/', {
      command: commandToExecute,
      use_sudo: terminalUseSudo.value
    })
    
    terminalHistory.value.push({
      command: commandToExecute,
      output: response.output || response.stdout || response.stderr || '',
      exit_status: response.exit_status || 0,
      success: response.success !== false,
      use_sudo: terminalUseSudo.value
    })
    
    // Actualizar path si es un comando cd
    if (commandToExecute.startsWith('cd ')) {
      const newPath = commandToExecute.substring(3).trim()
      if (newPath) {
        terminalPath.value = newPath.startsWith('/') ? newPath : `${terminalPath.value}/${newPath}`
      }
    }
    
    // Limpiar comando actual
    terminalCurrentCommand.value = ''
    terminalHistoryIndex.value = -1
    
    // Scroll al final
    setTimeout(() => {
      if (terminalOutput.value) {
        terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight
      }
    }, 10)
  } catch (error: any) {
    terminalHistory.value.push({
      command: commandToExecute,
      output: error?.data?.error || error?.message || 'Error ejecutando comando',
      exit_status: -1,
      success: false,
      use_sudo: terminalUseSudo.value
    })
    terminalCurrentCommand.value = ''
    terminalHistoryIndex.value = -1
  } finally {
    terminalExecuting.value = false
    setTimeout(() => {
      if (terminalInput.value) {
        terminalInput.value.focus()
      }
    }, 10)
  }
}

const clearTerminal = () => {
  terminalHistory.value = []
  terminalCurrentCommand.value = ''
}

const terminalHistoryUp = () => {
  if (terminalHistory.value.length === 0) return
  if (terminalHistoryIndex.value < terminalHistory.value.length - 1) {
    terminalHistoryIndex.value++
  }
  const history = terminalHistory.value.filter(h => h.command).map(h => h.command).reverse()
  if (history[terminalHistoryIndex.value]) {
    terminalCurrentCommand.value = history[terminalHistoryIndex.value]
  }
}

const terminalHistoryDown = () => {
  if (terminalHistoryIndex.value > 0) {
    terminalHistoryIndex.value--
    const history = terminalHistory.value.filter(h => h.command).map(h => h.command).reverse()
    if (history[terminalHistoryIndex.value]) {
      terminalCurrentCommand.value = history[terminalHistoryIndex.value]
    }
  } else {
    terminalHistoryIndex.value = -1
    terminalCurrentCommand.value = ''
  }
}

// ========== API KEYS FUNCTIONS ==========
const newApiKey = ref({
  nit: '',
  nombre_cliente: '',
  dias_validez: 365
})

const loadApiKeys = async () => {
  loadingApiKeys.value = true
  try {
    const response = await api.get<any>('/api/api-keys/listar_api_keys/')
    const data = response.api_keys || []
    apiKeys.value = data.map((key: any) => ({
      ...key,
      showKey: false,
      api_key_masked: key.api_key ? `${key.api_key.substring(0, 8)}...${key.api_key.substring(key.api_key.length - 4)}` : '',
      expirada: new Date(key.fecha_caducidad) < new Date(),
      empresas_asociadas_count: key.empresas_asociadas?.length || 0
    }))
  } catch (error: any) {
    console.error('Error cargando API Keys:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar API Keys',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingApiKeys.value = false
  }
}

const createApiKey = async () => {
  creatingApiKey.value = true
  try {
    const response = await api.post('/api/api-keys/generar_api_key/', newApiKey.value)
    const Swal = (await import('sweetalert2')).default
    
    // Mostrar la API Key generada (solo se muestra una vez)
    await Swal.fire({
      title: '¡API Key Generada!',
      html: `
        <div style="text-align: left;">
          <p><strong>NIT:</strong> ${response.nit}</p>
          <p><strong>Cliente:</strong> ${response.nombre_cliente}</p>
          <p><strong>Empresas asociadas:</strong> ${response.empresas_asociadas || 0}</p>
          <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px;">
            <p style="margin-bottom: 5px;"><strong>API Key (GUARDA ESTA KEY):</strong></p>
            <code style="font-size: 0.9em; word-break: break-all;">${response.api_key}</code>
          </div>
          <p style="margin-top: 10px; color: #d32f2f; font-size: 0.9em;">
            ⚠️ Esta es la única vez que podrás ver esta clave. Guárdala en un lugar seguro.
          </p>
        </div>
      `,
      icon: 'success',
      confirmButtonText: 'Copiar y Cerrar',
      customClass: { container: 'swal-z-index-fix' },
      didOpen: () => {
        // Copiar automáticamente al portapapeles
        navigator.clipboard.writeText(response.api_key).catch(() => {})
      }
    })
    
    showCreateApiKey.value = false
    newApiKey.value = { nit: '', nombre_cliente: '', dias_validez: 365 }
    await loadApiKeys()
  } catch (error: any) {
    console.error('Error generando API Key:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al generar API Key',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    creatingApiKey.value = false
  }
}

const toggleApiKeyVisibility = (keyId: number) => {
  const key = apiKeys.value.find(k => k.id === keyId)
  if (key) {
    key.showKey = !key.showKey
  }
}

const copyApiKey = async (apiKey: string) => {
  try {
    await navigator.clipboard.writeText(apiKey)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Copiado',
      text: 'API Key copiada al portapapeles',
      icon: 'success',
      timer: 1500,
      showConfirmButton: false,
      customClass: { container: 'swal-z-index-fix' }
    })
  } catch (error) {
    console.error('Error copiando:', error)
  }
}

const regenerateApiKey = async (keyId: number) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Regenerar API Key?',
    text: 'Esto generará una nueva clave. La clave anterior dejará de funcionar.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, regenerar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      const key = apiKeys.value.find(k => k.id === keyId)
      if (!key) return
      
      const response = await api.post('/api/api-keys/generar_api_key/', {
        nit: key.nit,
        nombre_cliente: key.nombre_cliente,
        dias_validez: Math.ceil((new Date(key.fecha_caducidad).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
      })
      
      await Swal.fire({
        title: '¡API Key Regenerada!',
        html: `
          <div style="text-align: left;">
            <p><strong>Nueva API Key:</strong></p>
            <code style="font-size: 0.9em; word-break: break-all;">${response.api_key}</code>
            <p style="margin-top: 10px; color: #d32f2f; font-size: 0.9em;">
              ⚠️ Guarda esta nueva clave. La anterior ya no funcionará.
            </p>
          </div>
        `,
        icon: 'success',
        confirmButtonText: 'Copiar y Cerrar',
        customClass: { container: 'swal-z-index-fix' },
        didOpen: () => {
          navigator.clipboard.writeText(response.api_key).catch(() => {})
        }
      })
      
      await loadApiKeys()
    } catch (error: any) {
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al regenerar API Key',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

const toggleApiKeyStatus = async (keyId: number, newStatus: boolean) => {
  try {
    await api.post('/api/api-keys/revocar_api_key/', {
      api_key_id: keyId,
      revocar: !newStatus
    })
    await loadApiKeys()
  } catch (error: any) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cambiar estado',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const revokeApiKey = async (keyId: number) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Revocar API Key?',
    text: 'Esta acción no se puede deshacer. La API Key dejará de funcionar inmediatamente.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, revocar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#d32f2f',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.post('/api/api-keys/revocar_api_key/', {
        api_key_id: keyId,
        revocar: true
      })
      await Swal.fire({
        title: 'Revocada',
        text: 'API Key revocada exitosamente',
        icon: 'success',
        timer: 1500,
        showConfirmButton: false,
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadApiKeys()
    } catch (error: any) {
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al revocar API Key',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

// ========== ML MODELS FUNCTIONS ==========
const filteredMLModels = computed(() => {
  if (!mlFilterEmpresa.value) return mlModels.value
  return mlModels.value.filter(m => 
    m.empresa_servidor_id_original === Number(mlFilterEmpresa.value) || 
    m.empresa_servidor_id === Number(mlFilterEmpresa.value)
  )
})

const loadMLModels = async () => {
  loadingML.value = true
  try {
    // Por ahora, cargar desde el sistema de archivos o desde una lista
    // En el futuro, esto podría venir de un endpoint
    mlModels.value = []
    // TODO: Implementar carga de modelos desde backend
  } catch (error: any) {
    console.error('Error cargando modelos:', error)
  } finally {
    loadingML.value = false
  }
}

const trainModel = async (empresaId: number | string) => {
  if (!empresaId) return
  const empresaIdNum = Number(empresaId)
  trainingModel.value = empresaIdNum
  
  const Swal = (await import('sweetalert2')).default
  try {
    Swal.fire({
      title: 'Entrenando modelo...',
      html: 'Esto puede tardar varios minutos. Por favor, espera.',
      icon: 'info',
      allowOutsideClick: false,
      showConfirmButton: false,
      didOpen: () => {
        Swal.showLoading()
      },
      customClass: { container: 'swal-z-index-fix' }
    })
    
    const response = await api.post('/api/ml/entrenar_modelos/', {
      empresa_servidor_id: empresaIdNum
    })
    
    await Swal.fire({
      title: '¡Modelo Entrenado!',
      html: `
        <div style="text-align: left;">
          <p><strong>Estado:</strong> ${response.estado || 'Completado'}</p>
          ${response.prophet ? `<p><strong>Prophet:</strong> Entrenado</p>` : ''}
          ${response.xgboost ? `<p><strong>XGBoost:</strong> Entrenado</p>` : ''}
          ${response.mlflow_ui_url ? `
            <p style="margin-top: 10px;">
              <a href="${response.mlflow_ui_url}" target="_blank" style="color: #1976d2; text-decoration: underline;">
                📊 Ver en MLflow
              </a>
            </p>
          ` : ''}
        </div>
      `,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    
    await loadMLModels()
    newModelEmpresaId.value = ''
  } catch (error: any) {
    console.error('Error entrenando modelo:', error)
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al entrenar modelo',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    trainingModel.value = null
  }
}

const viewApiKeyEmpresas = async (keyId: number) => {
  const key = apiKeys.value.find(k => k.id === keyId)
  if (!key) return
  
  const Swal = (await import('sweetalert2')).default
  await Swal.fire({
    title: 'Empresas Asociadas',
    html: `
      <div style="text-align: left;">
        <p><strong>NIT:</strong> ${key.nit}</p>
        <p><strong>Total:</strong> ${key.empresas_asociadas_count} empresas</p>
        ${key.empresas_asociadas?.length > 0 ? `
          <ul style="margin-top: 10px;">
            ${key.empresas_asociadas.map((emp: any) => `
              <li>${emp.nombre} (${emp.nit}) - Año ${emp.anio_fiscal}</li>
            `).join('')}
          </ul>
        ` : '<p>No hay empresas asociadas</p>'}
      </div>
    `,
    icon: 'info',
    confirmButtonText: 'Cerrar',
    customClass: { container: 'swal-z-index-fix' }
  })
}

// ========== SERVER EDIT/DELETE FUNCTIONS ==========
const editServer = (server: Servidor) => {
  editingServer.value = { ...server }
  showEditServer.value = true
}

const updateServer = async () => {
  if (!editingServer.value) return
  creatingServer.value = true
  try {
    await api.put(`/api/servidores/${editingServer.value.id}/`, editingServer.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Éxito!',
      text: 'Servidor actualizado exitosamente',
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showEditServer.value = false
    editingServer.value = null
    await loadServers()
  } catch (error: any) {
    console.error('Error actualizando servidor:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al actualizar servidor',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    creatingServer.value = false
  }
}

const deleteServer = async (serverId: number) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar servidor?',
    text: 'Esta acción no se puede deshacer. Se eliminarán también todas las empresas asociadas.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#d32f2f',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.delete(`/api/servidores/${serverId}/`)
      await Swal.fire({
        title: 'Eliminado',
        text: 'Servidor eliminado exitosamente',
        icon: 'success',
        timer: 1500,
        showConfirmButton: false,
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadServers()
      await loadEmpresas()
    } catch (error: any) {
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar servidor',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

// ========== EMPRESA EXTRACT DATA FUNCTION ==========
const openExtractDataModal = (empresa: Empresa) => {
  selectedEmpresaForExtract.value = empresa
  const today = new Date()
  const lastYear = new Date(today.getFullYear() - 1, 0, 1)
  extractDateRange.value = {
    fecha_inicio: lastYear.toISOString().split('T')[0],
    fecha_fin: today.toISOString().split('T')[0]
  }
  showExtractDataModal.value = true
}

const extractData = async () => {
  if (!selectedEmpresaForExtract.value) return
  extractingData.value = true
  try {
    const response = await api.post('/api/sistema/extraer_datos/', {
      empresa_servidor_id: selectedEmpresaForExtract.value.id,
      fecha_inicio: extractDateRange.value.fecha_inicio,
      fecha_fin: extractDateRange.value.fecha_fin
    })
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Extracción completada!',
      html: `
        <div style="text-align: left;">
          <p><strong>Estado:</strong> ${response.estado}</p>
          <p><strong>Registros guardados:</strong> ${response.registros_guardados || 0}</p>
          <p><strong>Total encontrados:</strong> ${response.total_encontrados || 0}</p>
          ${response.chunks_procesados ? `<p><strong>Chunks procesados:</strong> ${response.chunks_procesados}</p>` : ''}
        </div>
      `,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showExtractDataModal.value = false
    selectedEmpresaForExtract.value = null
  } catch (error: any) {
    console.error('Error extrayendo datos:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al extraer datos',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    extractingData.value = false
  }
}

onMounted(async () => {
  // Cargar servidores primero para poder mapear correctamente los nombres
  await loadServers()
  // Luego cargar empresas (necesitan los servidores para mapear nombres)
  await loadEmpresas()
  loadVpnConfigs()
  loadApiKeys()
  loadMLModels()
  // Cargar información del sistema si estamos en la pestaña de servicios
  if (activeSection.value === 'servicios') {
    loadSystemInfo()
    loadSystemdServices()
    loadPm2Processes()
  }
})
</script>

<style scoped>
.admin-dashboard {
  min-height: 100vh;
  background: #ffffff;
}

/* API Keys Styles */
.api-key-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.api-key-masked,
.api-key-visible {
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  padding: 0.25rem 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
  flex: 1;
  word-break: break-all;
}

.api-key-visible {
  background: #e8f5e9;
  color: #2e7d32;
}

.btn-tiny {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  min-width: auto;
}

.text-danger {
  color: #d32f2f;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 12px;
  font-size: 0.85em;
  font-weight: 500;
}

.admin-header {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 1.75rem 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-content {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.brand-logo {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 0.75rem;
  color: #4b5563;
  flex-shrink: 0;
}

.brand-logo svg {
  width: 28px;
  height: 28px;
}

.admin-header h1 {
  font-size: 1.75rem;
  font-weight: 800;
  color: #1f2937;
  margin: 0 0 0.25rem 0;
}

.header-subtitle {
  color: #6b7280;
  font-size: 0.875rem;
  margin: 0;
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info {
  color: #4b5563;
  font-weight: 500;
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  border-radius: 0.5rem;
  font-size: 0.875rem;
}

.btn-logout {
  padding: 0.625rem 1.25rem;
  background: #1f2937;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.875rem;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-logout:hover {
  background: #374151;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.admin-nav {
  background: white;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 2rem;
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
}

.nav-btn {
  padding: 1rem 1.5rem;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  font-weight: 500;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  white-space: nowrap;
}

.nav-btn:hover {
  color: #1f2937;
  background: #f9fafb;
}

.nav-btn.active {
  color: #1f2937;
  border-bottom-color: #1f2937;
  background: #f3f4f6;
}

.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-icon svg {
  width: 100%;
  height: 100%;
}

.admin-main {
  max-width: 1600px;
  margin: 0 auto;
  padding: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.section h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.actions-bar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.search-input {
  padding: 0.625rem 1rem;
  border: 1.5px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 0.95rem;
  min-width: 300px;
  transition: all 0.2s;
  background: white;
}

.search-input:focus {
  outline: none;
  border-color: #9ca3af;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

.btn-primary,
.btn-secondary {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-primary {
  background: #1f2937;
  color: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-primary:hover:not(:disabled) {
  background: #374151;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #4b5563;
  border: 1.5px solid #e5e7eb;
}

.btn-secondary:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.servers-grid,
.scrapers-grid,
.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.server-card,
.scraper-card,
.model-card {
  background: white;
  border-radius: 1rem;
  padding: 1.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: all 0.2s;
  border: 1px solid #e5e7eb;
}

.server-card:hover,
.scraper-card:hover,
.model-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.server-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.server-card h3,
.scraper-card h3,
.model-card h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 0.5rem 0;
}

.server-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-firebird {
  background: #f3f4f6;
  color: #4b5563;
}

.badge-postgresql {
  background: #f3f4f6;
  color: #4b5563;
}

.server-info {
  margin: 1rem 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.9rem;
}

.info-label {
  color: #6b7280;
  font-weight: 500;
}

.info-value {
  color: #1f2937;
  font-weight: 600;
}

.server-actions,
.model-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid #f1f5f9;
}

.btn-small {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.btn-small.btn-primary {
  background: #1f2937;
  color: white;
}

.btn-small.btn-primary:hover:not(:disabled) {
  background: #374151;
}

.btn-small.btn-secondary {
  background: #f3f4f6;
  color: #4b5563;
  border: 1.5px solid #e5e7eb;
}

.btn-small.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-small:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.table-container {
  background: white;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  text-align: left;
  padding: 1rem 1.25rem;
  background: #f9fafb;
  color: #4b5563;
  font-weight: 600;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #e5e7eb;
}

.data-table td {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #f3f4f6;
  color: #1f2937;
}

.data-table tbody tr:hover {
  background: #f9fafb;
}

.data-table code {
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #1f2937;
  font-weight: 600;
}

.scraper-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 1rem;
  color: #4b5563;
  margin-bottom: 1rem;
}

.scraper-icon svg {
  width: 32px;
  height: 32px;
}

.spinner-icon {
  width: 16px;
  height: 16px;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}

.progress-bar > div {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #45a049);
  transition: width 0.3s ease;
  border-radius: 10px;
}

.scraper-card p,
.model-info {
  color: #6b7280;
  line-height: 1.6;
  margin: 0.5rem 0;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #6b7280;
}

.loading-state p,
.empty-state p {
  font-size: 1.125rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.modal-content {
  background: white;
  border-radius: 1rem;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.75rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 2rem;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.modal-form {
  padding: 1.75rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #374151;
  font-weight: 600;
  font-size: 0.875rem;
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: #6b7280;
  font-size: 0.75rem;
}

.form-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1.5px solid #e5e7eb;
  border-radius: 0.5rem;
  font-size: 0.95rem;
  transition: all 0.2s;
  background: white;
}

.form-input:focus {
  outline: none;
  border-color: #9ca3af;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.status-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-active {
  background: #d1fae5;
  color: #065f46;
}

.status-inactive {
  background: #fee2e2;
  color: #991b1b;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-danger {
  background: #ef4444;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.btn-danger:hover {
  background: #dc2626;
}

@media (max-width: 768px) {
  .admin-header {
    padding: 1.5rem;
  }
  
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .admin-main {
    padding: 1rem;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .servers-grid,
  .scrapers-grid,
  .models-grid {
    grid-template-columns: 1fr;
  }

  .modal-overlay {
    padding: 1rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;
  }

  .action-buttons button {
    width: 100%;
  }
}

/* Estilos para VPN */
.name-cell {
  position: relative;
}

.editable-name {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  transition: background 0.2s;
}

.editable-name:hover {
  background: #f3f4f6;
}

.edit-icon {
  opacity: 0;
  transition: opacity 0.2s;
  width: 12px;
  height: 12px;
}

.editable-name:hover .edit-icon {
  opacity: 0.5;
}

.edit-name-input {
  display: inline-block;
}

.inline-input {
  padding: 0.25rem 0.5rem;
  border: 1.5px solid #1f2937;
  border-radius: 0.25rem;
  font-size: 0.95rem;
  font-weight: 600;
  min-width: 150px;
}

.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.connection-status.connected .status-dot {
  background: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
}

.connection-status.disconnected .status-dot {
  background: #ef4444;
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.connection-status.unknown .status-dot {
  background: #6b7280;
  box-shadow: 0 0 0 2px rgba(107, 114, 128, 0.2);
}

.traffic-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.875rem;
}

.traffic-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.traffic-label {
  font-weight: 600;
  color: #6b7280;
  min-width: 20px;
}

.traffic-value {
  color: #1f2937;
  font-weight: 500;
}

.handshake-time {
  font-size: 0.875rem;
  color: #4b5563;
}

.handshake-time.never {
  color: #9ca3af;
  font-style: italic;
}

.btn-info {
  background: #3b82f6;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.btn-info:hover {
  background: #2563eb;
}

.stats-modal {
  max-width: 700px;
}

.stats-content {
  padding: 1.75rem;
}

.stat-section {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.stat-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.stat-section h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 0.5rem 0;
}

.stat-section h4 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 1rem 0;
}

.stat-ip {
  color: #6b7280;
  font-size: 0.875rem;
  margin: 0;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f3f4f6;
}

.stat-row:last-child {
  border-bottom: none;
}

.stat-label {
  font-weight: 500;
  color: #6b7280;
  font-size: 0.875rem;
}

.stat-value {
  font-weight: 600;
  color: #1f2937;
  font-size: 0.95rem;
}

.stat-value.connected {
  color: #10b981;
}

.stat-value.disconnected {
  color: #ef4444;
}

/* Estilos para modal de detalles del servidor */
.server-details-modal {
  max-width: 900px;
}

.server-details-content {
  padding: 1.75rem;
}

.detail-section {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.detail-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.detail-section h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 1rem 0;
}

.section-header-inline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.badge-count {
  padding: 0.375rem 0.75rem;
  background: #f3f4f6;
  color: #4b5563;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.detail-value {
  font-size: 0.95rem;
  color: #1f2937;
  font-weight: 600;
}

.details-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.details-table th {
  text-align: left;
  padding: 0.75rem;
  background: #f9fafb;
  color: #4b5563;
  font-weight: 600;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #e5e7eb;
}

.details-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #f3f4f6;
  color: #1f2937;
  font-size: 0.875rem;
}

.details-table tbody tr:hover {
  background: #f9fafb;
}

.empty-state-small {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.filter-select {
  padding: 0.5rem 0.75rem;
  border: 1.5px solid #d1d5db;
  border-radius: 0.5rem;
  background: white;
  color: #1f2937;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-select:hover {
  border-color: #9ca3af;
}

.filter-select:focus {
  outline: none;
  border-color: #4b5563;
  box-shadow: 0 0 0 3px rgba(75, 85, 99, 0.1);
}

.sortable {
  cursor: pointer;
  user-select: none;
  position: relative;
  padding-right: 1.5rem !important;
}

.sortable:hover {
  background: #f3f4f6;
}

.sort-icon {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.875rem;
  color: #4b5563;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
}

.pagination-info {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.page-info {
  font-size: 0.875rem;
  color: #4b5563;
  font-weight: 600;
  padding: 0 0.75rem;
}

.status-warning {
  background: #fef3c7;
  color: #92400e;
}

@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .server-details-modal {
    max-width: 95%;
  }
  
  .terminal-container {
    height: 500px;
  }
}

.terminal-container {
  display: flex;
  flex-direction: column;
  height: 600px;
  background: #1f2937;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid #374151;
}

.terminal-output {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  color: #f9fafb;
  background: #111827;
}

.terminal-entry {
  margin-bottom: 1rem;
}

.terminal-prompt {
  margin-bottom: 0.25rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.prompt-user {
  color: #10b981;
  font-weight: 600;
}

.prompt-host {
  color: #3b82f6;
  font-weight: 600;
}

.prompt-path {
  color: #f59e0b;
}

.prompt-separator {
  color: #6b7280;
}

.prompt-sudo {
  color: #ef4444;
  font-weight: 600;
  margin-left: 0.5rem;
}

.terminal-command {
  color: #f9fafb;
  margin-bottom: 0.5rem;
  padding-left: 0.5rem;
}

.terminal-output-text {
  color: #d1d5db;
  white-space: pre-wrap;
  word-wrap: break-word;
  padding-left: 0.5rem;
  margin-top: 0.25rem;
}

.terminal-output-text.terminal-error {
  color: #f87171;
}

.terminal-exit-status {
  color: #9ca3af;
  font-size: 0.75rem;
  padding-left: 0.5rem;
  margin-top: 0.25rem;
  font-style: italic;
}

.terminal-executing {
  color: #fbbf24;
  padding-left: 0.5rem;
  font-style: italic;
}

.terminal-input-container {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  background: #111827;
  border-top: 1px solid #374151;
}

.terminal-input {
  flex: 1;
  background: #1f2937;
  border: 1px solid #374151;
  color: #f9fafb;
  padding: 0.75rem;
  border-radius: 0.25rem;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.terminal-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.terminal-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.terminal-send-btn {
  padding: 0.75rem 1.5rem;
  min-width: auto;
}

.terminal-sudo-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.terminal-sudo-toggle input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.terminal-sudo-toggle span {
  color: #4b5563;
  font-size: 0.875rem;
  font-weight: 500;
}

/* Estilos para sección de Logs */
.logs-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 0.5rem;
}

.logs-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #6b7280;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: -0.5rem;
}

.logs-tab:hover {
  color: #3b82f6;
  background: #f3f4f6;
  border-radius: 0.5rem 0.5rem 0 0;
}

.logs-tab.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  background: #eff6ff;
  border-radius: 0.5rem 0.5rem 0 0;
}

.logs-filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #4b5563;
  white-space: nowrap;
}

.logs-container {
  display: flex;
  flex-direction: column;
  height: 600px;
  background: #1f2937;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid #374151;
}

.logs-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.logs-text {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  font-family: 'Courier New', monospace;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: #f9fafb;
  background: #111827;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.logs-text.filtered {
  background: #1a1f2e;
}

.logs-auto-refresh-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  transition: background 0.2s;
}

.logs-auto-refresh-toggle:hover {
  background: #f3f4f6;
}

.logs-auto-refresh-toggle input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.logs-auto-refresh-toggle span {
  color: #4b5563;
  font-size: 0.875rem;
  font-weight: 500;
}

/* Estilos para Tareas en Tiempo Real */
.realtime-tasks-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.realtime-header {
  display: flex;
  gap: 1rem;
  align-items: center;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
}

.realtime-tasks-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-height: 600px;
  overflow-y: auto;
}

.realtime-section {
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  border: 1px solid #e5e7eb;
}

.realtime-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: #1f2937;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
}

.workers-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.worker-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border-radius: 0.375rem;
  border: 1px solid #e5e7eb;
}

.worker-name {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  color: #1f2937;
  font-weight: 600;
}

.worker-status {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
}

.worker-status.active {
  color: #10b981;
  background: #d1fae5;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.task-item {
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  transition: all 0.2s;
}

.task-item:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.task-item.active {
  border-left: 4px solid #10b981;
  background: #f0fdf4;
}

.task-item.scheduled {
  border-left: 4px solid #f59e0b;
  background: #fffbeb;
}

.task-item.reserved {
  border-left: 4px solid #3b82f6;
  background: #eff6ff;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.task-name {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  font-weight: 600;
  color: #1f2937;
}

.task-status {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
}

.task-status.active {
  color: #10b981;
  background: #d1fae5;
}

.task-status.scheduled {
  color: #f59e0b;
  background: #fef3c7;
}

.task-status.reserved {
  color: #3b82f6;
  background: #dbeafe;
}

.task-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #6b7280;
}

.task-details strong {
  color: #4b5563;
  font-weight: 600;
}

.task-details code {
  background: #f3f4f6;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  color: #1f2937;
  font-family: 'Courier New', monospace;
}

.empty-state-small {
  padding: 2rem;
  text-align: center;
  color: #9ca3af;
  font-size: 0.875rem;
}
</style>
