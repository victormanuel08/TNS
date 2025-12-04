<template>
  <div class="admin-dashboard">
    <ToastContainer />
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
          <ServidorCard
            v-for="server in servers"
            :key="server.id"
            :server="server"
            :scanning="scanningServer === server.id"
            :has-active-task="!!activeScanTasks[server.id]"
            @scan="scanEmpresas"
            @view-empresas="viewServerEmpresas"
            @edit="editServer"
            @details="viewServerDetails"
            @delete="deleteServer"
          />
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
                      <button class="btn-small btn-secondary" @click="editEmpresaSQL(empresa)" title="Editar Consulta SQL">
                        📝 SQL
                      </button>
                      <button class="btn-small btn-secondary" @click="editEmpresaConfig(empresa)" title="Editar Configuración">
                        ⚙️ Config
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

        <!-- Tabs para Usuarios -->
        <Tabs
          :tabs="[
            { id: 'usuarios', label: '👥 Usuarios' },
            { id: 'permisos', label: '🔐 Permisos' },
            { id: 'tenant-profiles', label: '🏢 Tenant Profiles' }
          ]"
          :active-tab="userActiveTab"
          @change="userActiveTab = $event"
        />

        <!-- Tab: Usuarios -->
        <div v-if="userActiveTab === 'usuarios'">
          <div v-if="loadingUsers" class="loading-state">
            <p>Cargando usuarios...</p>
          </div>

          <div v-else-if="filteredUsers.length === 0" class="empty-state">
            <p>No hay usuarios</p>
          </div>

          <div v-else>
            <UsuariosTable
              :usuarios="paginatedUsers"
              :current-user-id="user?.id"
              @edit="editUser"
              @reset-password="resetUserPassword"
              @view-permisos="viewUserPermisos"
              @view-tenant-profile="viewUserTenantProfile"
              @delete="deleteUser"
            />
            <Pagination
              v-if="usuariosPagination.totalPages.value > 1"
              :current-page="usuariosPagination.currentPage.value"
              :total-pages="usuariosPagination.totalPages.value"
              :total="filteredUsers.length"
              :items-per-page="usuariosItemsPerPage"
              @go-to="usuariosPagination.goToPage"
              @next="usuariosPagination.nextPage"
              @previous="usuariosPagination.previousPage"
            />
          </div>
        </div>

        <!-- Tab: Permisos -->
        <div v-if="userActiveTab === 'permisos'">
          <div class="section-header">
            <div class="actions-bar">
              <button class="btn-primary" @click="showCreatePermiso = true">
                <span>+</span> Crear Permiso
              </button>
              <button class="btn-secondary" @click="loadPermisos" :disabled="loadingPermisos">
                <span v-if="loadingPermisos">⟳</span>
                <span v-else>↻</span>
                Actualizar
              </button>
            </div>
          </div>

          <div v-if="loadingPermisos" class="loading-state">
            <p>Cargando permisos...</p>
          </div>
          
          <div v-else-if="permisosUsuarios.length === 0" class="empty-state">
            <p>No hay permisos registrados</p>
          </div>
          
          <div v-else class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Empresa</th>
                  <th>Permisos</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="permiso in permisosUsuarios" :key="permiso.id">
                  <td>
                    <strong>{{ permiso.usuario_username }}</strong><br>
                    <small style="color: #666;">{{ permiso.usuario_email || 'Sin email' }}</small>
                  </td>
                  <td>
                    <strong>{{ permiso.empresa_servidor_nombre }}</strong><br>
                    <small style="color: #666;">NIT: {{ permiso.empresa_servidor_nit }}</small>
                  </td>
                  <td>
                    <span class="badge" v-if="permiso.puede_consultar">Consultar</span>
                    <span class="badge" v-if="permiso.puede_crear">Crear</span>
                    <span class="badge" v-if="permiso.puede_editar">Editar</span>
                    <span class="badge" v-if="permiso.puede_eliminar">Eliminar</span>
                  </td>
                  <td>
                    <div class="action-buttons">
                      <button class="btn-small btn-secondary" @click="editPermiso(permiso)" title="Editar">
                        ✏️
                      </button>
                      <button class="btn-small btn-danger" @click="deletePermiso(permiso)" title="Eliminar">
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tab: Tenant Profiles -->
        <div v-if="userActiveTab === 'tenant-profiles'">
          <div class="section-header">
            <div class="actions-bar">
              <button class="btn-primary" @click="showCreateTenantProfile = true">
                <span>+</span> Crear Tenant Profile
              </button>
              <button class="btn-secondary" @click="loadTenantProfiles" :disabled="loadingTenantProfiles">
                <span v-if="loadingTenantProfiles">⟳</span>
                <span v-else>↻</span>
                Actualizar
              </button>
            </div>
          </div>

          <div v-if="loadingTenantProfiles" class="loading-state">
            <p>Cargando tenant profiles...</p>
          </div>
          
          <div v-else-if="tenantProfiles.length === 0" class="empty-state">
            <p>No hay tenant profiles registrados</p>
          </div>
          
          <div v-else class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Usuario</th>
                  <th>Subdomain</th>
                  <th>Template</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="profile in tenantProfiles" :key="profile.id">
                  <td>
                    <strong>{{ profile.user_username }}</strong><br>
                    <small style="color: #666;">{{ profile.user_email || 'Sin email' }}</small>
                  </td>
                  <td><code>{{ profile.subdomain }}</code></td>
                  <td>
                    <span class="badge">{{ profile.preferred_template || 'pro' }}</span>
                  </td>
                  <td>
                    <div class="action-buttons">
                      <button class="btn-small btn-secondary" @click="editTenantProfile(profile)" title="Editar">
                        ✏️
                      </button>
                      <button class="btn-small btn-danger" @click="deleteTenantProfile(profile)" title="Eliminar">
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
        
        <div v-else>
          <ApiKeysTable
            :api-keys="apiKeys"
            @toggle-visibility="toggleApiKeyVisibility"
            @copy="copyApiKey"
            @view-empresas="viewApiKeyEmpresas"
            @regenerate="regenerateApiKey"
            @toggle-status="toggleApiKeyStatus"
            @manage-calendario-nits="manageCalendarioNits"
            @revoke="revokeApiKey"
          />
        </div>
      </section>

      <!-- Dominios -->
      <section v-if="activeSection === 'dominios'" class="section">
        <div class="section-header">
          <h2>Gestión de Dominios</h2>
          <div class="actions-bar">
            <button class="btn-primary" @click="showCreateDominio = true">
              <span>+</span> Crear Dominio
            </button>
            <button class="btn-secondary" @click="loadDominios" :disabled="loadingDominios">
              <span v-if="loadingDominios">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingDominios" class="loading-state">
          <p>Cargando dominios...</p>
        </div>
        
        <div v-else-if="dominios.length === 0" class="empty-state">
          <p>No hay dominios registrados</p>
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Dominio</th>
                <th>NIT</th>
                <th>Servidor</th>
                <th>Empresa</th>
                <th>Año Fiscal</th>
                <th>Modo</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="dominio in dominios" :key="dominio.id">
                <td><code>{{ dominio.dominio }}</code></td>
                <td>{{ dominio.nit || '-' }}</td>
                <td>
                  <span v-if="dominio.servidor_nombre" class="badge">{{ dominio.servidor_nombre }}</span>
                  <span v-else class="text-muted">Todos</span>
                </td>
                <td>{{ dominio.empresa_servidor_nombre || '-' }}</td>
                <td>{{ dominio.anio_fiscal || '-' }}</td>
                <td>
                  <span class="status-badge" :class="{
                    'status-active': dominio.modo === 'ecommerce',
                    'status-warning': dominio.modo === 'autopago',
                    'status-inactive': dominio.modo === 'pro'
                  }">
                    {{ dominio.modo === 'ecommerce' ? 'E-commerce' : dominio.modo === 'autopago' ? 'Autopago' : 'Profesional' }}
                  </span>
                </td>
                <td>
                  <span class="status-badge" :class="dominio.activo ? 'status-active' : 'status-inactive'">
                    {{ dominio.activo ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td>
                  <div class="action-buttons">
                    <button class="btn-small btn-secondary" @click="editDominio(dominio)" title="Editar">
                      ✏️
                    </button>
                    <button class="btn-small btn-danger" @click="deleteDominio(dominio)" title="Eliminar">
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Pasarelas de Pago -->
      <section v-if="activeSection === 'pasarelas'" class="section">
        <div class="section-header">
          <h2>Gestión de Pasarelas de Pago</h2>
          <div class="actions-bar">
            <button class="btn-primary" @click="showCreatePasarela = true">
              <span>+</span> Crear Pasarela
            </button>
            <button class="btn-secondary" @click="loadPasarelas" :disabled="loadingPasarelas">
              <span v-if="loadingPasarelas">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingPasarelas" class="loading-state">
          <p>Cargando pasarelas...</p>
        </div>
        
        <div v-else-if="pasarelas.length === 0" class="empty-state">
          <p>No hay pasarelas registradas</p>
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Estado</th>
                <th>Configuración</th>
                <th>Fecha Creación</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pasarela in pasarelas" :key="pasarela.id">
                <td><code>{{ pasarela.codigo }}</code></td>
                <td><strong>{{ pasarela.nombre }}</strong></td>
                <td>
                  <span class="status-badge" :class="pasarela.activa ? 'status-active' : 'status-inactive'">
                    {{ pasarela.activa ? 'Activa' : 'Inactiva' }}
                  </span>
                </td>
                <td>
                  <button class="btn-small btn-info" @click="viewPasarelaConfig(pasarela)" title="Ver configuración">
                    👁️ Ver
                  </button>
                </td>
                <td>{{ formatDate(pasarela.fecha_creacion) }}</td>
                <td>
                  <div class="action-buttons">
                    <button class="btn-small btn-secondary" @click="editPasarela(pasarela)" title="Editar">
                      ✏️
                    </button>
                    <button class="btn-small btn-danger" @click="deletePasarela(pasarela)" title="Eliminar">
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>


      <!-- RUTs -->
      <section v-if="activeSection === 'ruts'" class="section">
        <div class="section-header">
          <h2>Gestión de RUTs (Registro Único Tributario)</h2>
          <div class="actions-bar">
            <button class="btn-primary" @click="showUploadRUT = true">
              <span>📄</span> Subir RUT PDF
            </button>
            <button class="btn-secondary" @click="loadRuts" :disabled="loadingRuts">
              <span v-if="loadingRuts">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingRuts" class="loading-state">
          <p>Cargando RUTs...</p>
        </div>
        
        <div v-else-if="ruts.length === 0" class="empty-state">
          <p>No hay RUTs registrados</p>
          <p style="margin-top: 10px; color: #666; font-size: 0.9em;">
            Sube un PDF de RUT para comenzar. El sistema detectará automáticamente el NIT.
          </p>
        </div>
        
        <div v-else class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>NIT</th>
                <th>Razón Social</th>
                <th>Nombre Comercial</th>
                <th>Ciudad</th>
                <th>Empresas Asociadas</th>
                <th>PDF</th>
                <th>Última Actualización</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rut in ruts" :key="rut.id">
                <td>
                  <code>{{ rut.nit }}-{{ rut.dv }}</code><br>
                  <small style="color: #666;">Normalizado: {{ rut.nit_normalizado }}</small>
                </td>
                <td><strong>{{ rut.razon_social }}</strong></td>
                <td>{{ rut.nombre_comercial || '-' }}</td>
                <td>
                  {{ rut.ciudad_nombre || '-' }}<br>
                  <small style="color: #666;">{{ rut.departamento_nombre || '' }}</small>
                </td>
                <td>
                  <span class="status-badge status-active">
                    {{ rut.empresas_asociadas?.length || 0 }} empresa(s)
                  </span>
                </td>
                <td>
                  <a 
                    v-if="rut.archivo_pdf_url" 
                    :href="rut.archivo_pdf_url" 
                    target="_blank"
                    class="btn-small btn-info"
                    title="Ver PDF"
                  >
                    📄 Ver PDF
                  </a>
                  <span v-else style="color: #999;">Sin PDF</span>
                </td>
                <td>{{ formatDate(rut.fecha_actualizacion) }}</td>
                <td>
                  <div class="action-buttons">
                    <button class="btn-small btn-info" @click="viewRUTDetails(rut)" title="Ver detalles">
                      👁️
                    </button>
                    <button class="btn-small btn-secondary" @click="editRUT(rut)" title="Editar">
                      ✏️
                    </button>
                    <button class="btn-small btn-danger" @click="deleteRUT(rut)" title="Eliminar">
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Calendario Tributario -->
      <section v-if="activeSection === 'calendario-tributario'" class="section">
        <div class="section-header">
          <h2>Gestión de Calendario Tributario</h2>
          <div class="actions-bar">
            <button class="btn-primary" @click="showUploadCalendario = true">
              <span>📅</span> Cargar Excel del Calendario
            </button>
            <button class="btn-secondary" @click="loadCalendarioTributario" :disabled="loadingCalendario">
              <span v-if="loadingCalendario">⟳</span>
              <span v-else>↻</span>
              Actualizar
            </button>
          </div>
        </div>
        
        <div v-if="loadingCalendario" class="loading-state">
          <p>Cargando calendario tributario...</p>
        </div>
        
        <div v-else-if="vigenciasTributarias.length === 0" class="empty-state">
          <p>No hay vigencias tributarias registradas</p>
          <p style="margin-top: 10px; color: #666; font-size: 0.9em;">
            Carga un Excel con el calendario tributario para comenzar. 
            El sistema detectará automáticamente las empresas asociadas por NIT.
          </p>
        </div>
        
        <div v-else>
          <CalendarioTributarioTable
            :vigencias="filteredAndSortedVigencias"
            :sort-by="calendarioSortBy"
            :sort-order="calendarioSortOrder"
            :filters="calendarioFilters"
            @sort="sortCalendario"
            @filter-change="(f) => calendarioFilters = f"
          />
        </div>
      </section>

      <!-- Backups S3 -->
      <section v-if="activeSection === 'backups-s3'" class="section">
        <div class="section-header">
          <h2>Backups S3 por Empresa (NIT)</h2>
        </div>

        <div class="two-column-layout">
          <!-- Configuración S3 -->
          <div class="card">
            <h3>Configuración S3</h3>
            <p class="small-muted">
              Un solo bucket global para todas las empresas. El límite de espacio se aplica por NIT normalizado, sumando todos los años y carpetas.
            </p>

            <div v-if="loadingS3Config" class="loading-state">
              <p>Cargando configuración S3...</p>
            </div>

            <div v-else>
              <div class="s3-config-form">
                <div class="form-group">
                  <label>
                    <span class="label-text">Nombre de configuración</span>
                    <input
                      v-model="activeS3Config.nombre"
                      type="text"
                      placeholder="Backups Principal"
                      class="form-input"
                    />
                  </label>
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label>
                      <span class="label-text">Bucket S3</span>
                      <input
                        v-model="activeS3Config.bucket_name"
                        type="text"
                        placeholder="mi-bucket-backups"
                        class="form-input"
                      />
                    </label>
                  </div>
                  <div class="form-group">
                    <label>
                      <span class="label-text">Región</span>
                      <input
                        v-model="activeS3Config.region"
                        type="text"
                        placeholder="us-east-1"
                        class="form-input"
                      />
                    </label>
                  </div>
                </div>

                <div class="form-group">
                  <label>
                    <span class="label-text">Access Key ID</span>
                    <input
                      v-model="activeS3Config.access_key_id"
                      type="text"
                      placeholder="AKIA..."
                      class="form-input"
                    />
                  </label>
                </div>

                <div class="form-group">
                  <label>
                    <span class="label-text">Secret Access Key</span>
                    <input
                      v-model="activeS3Config.secret_access_key"
                      type="password"
                      placeholder="••••••••"
                      class="form-input"
                    />
                    <small class="form-hint">Deja vacío para mantener el valor actual</small>
                  </label>
                </div>

                <div class="form-group">
                  <label>
                    <span class="label-text">Endpoint URL (opcional)</span>
                    <input
                      v-model="activeS3Config.endpoint_url"
                      type="text"
                      placeholder="https://s3.amazonaws.com o URL de MinIO"
                      class="form-input"
                    />
                    <small class="form-hint">Solo necesario para S3-compatible (MinIO, etc.)</small>
                  </label>
                </div>

                <div class="form-group checkbox-group">
                  <label class="checkbox-label">
                    <input
                      v-model="activeS3Config.activo"
                      type="checkbox"
                      class="checkbox-input"
                    />
                    <span class="checkbox-text">Configuración activa</span>
                  </label>
                </div>
              </div>

              <div class="actions-bar" style="margin-top: 16px;">
                <button
                  class="btn-primary"
                  @click="saveS3Config"
                  :disabled="savingS3Config"
                >
                  <span v-if="savingS3Config">⟳</span>
                  <span v-else>💾</span>
                  Guardar Configuración
                </button>
              </div>
            </div>
          </div>

          <!-- Backups por empresa -->
          <div class="card">
            <h3>Backups por Empresa</h3>

            <div class="actions-bar">
              <select
                v-model.number="selectedBackupEmpresaId"
                class="filter-select"
              >
                <option :value="null">Selecciona una empresa</option>
                <option
                  v-for="empresa in empresas"
                  :key="empresa.id"
                  :value="empresa.id"
                >
                  {{ empresa.nombre }} ({{ empresa.nit || empresa.nit_normalizado }}) - {{ empresa.anio_fiscal }}
                </option>
              </select>

              <button
                class="btn-secondary"
                @click="reloadBackupsAndStats"
                :disabled="!selectedBackupEmpresaId || loadingBackupsS3"
              >
                <span v-if="loadingBackupsS3">⟳</span>
                <span v-else>↻</span>
                Actualizar
              </button>

              <button
                class="btn-primary"
                @click="triggerBackupForSelectedEmpresa"
                :disabled="!selectedBackupEmpresaId || triggeringBackup"
              >
                <span v-if="triggeringBackup">⏳</span>
                <span v-else>📦</span>
                Crear Backup Ahora
              </button>
            </div>

            <div v-if="!selectedBackupEmpresaId" class="empty-state">
              <p>Selecciona una empresa para ver sus backups y estadísticas.</p>
            </div>

            <div v-else>
              <!-- Estadísticas -->
              <div v-if="backupStats" class="stats-grid">
                <div class="stat-card">
                  <span class="stat-label">Uso actual</span>
                  <span class="stat-value">
                    {{ backupStats.tamano_actual_gb.toFixed(2) }} GB
                  </span>
                </div>
                <div class="stat-card">
                  <span class="stat-label">Límite</span>
                  <span class="stat-value">
                    {{ backupStats.limite_gb }} GB
                  </span>
                </div>
                <div class="stat-card">
                  <span class="stat-label">Estado</span>
                  <span
                    class="status-badge"
                    :class="backupStats.excede_limite ? 'status-error' : 'status-active'"
                  >
                    {{ backupStats.excede_limite ? 'Límite excedido' : 'Dentro del límite' }}
                  </span>
                </div>
                <div class="stat-card">
                  <span class="stat-label">Total de Backups</span>
                  <span class="stat-value">
                    {{ backupStats.total_backups }}
                  </span>
                </div>
              </div>

              <!-- Tabla de backups -->
              <div class="table-container" style="margin-top: 16px;">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Archivo</th>
                      <th>Tamaño</th>
                      <th>Año Fiscal</th>
                      <th>Estado</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="backupsS3.length === 0">
                      <td colspan="6" class="text-center">
                        No hay backups registrados para esta empresa.
                      </td>
                    </tr>
                    <tr v-for="backup in backupsS3" :key="backup.id">
                      <td>{{ formatDate(backup.fecha_backup) }}</td>
                      <td>
                        <code>{{ backup.nombre_archivo }}</code>
                      </td>
                      <td>
                        {{ backup.tamano_gb.toFixed(2) }} GB
                        <br />
                        <small style="color:#666;">
                          {{ backup.tamano_mb.toFixed(2) }} MB
                        </small>
                      </td>
                      <td>{{ backup.anio_fiscal }}</td>
                      <td>
                        <span
                          class="status-badge"
                          :class="{
                            'status-active': backup.estado === 'completado',
                            'status-warning': backup.estado === 'en_proceso',
                            'status-error': backup.estado === 'fallido'
                          }"
                        >
                          {{ backup.estado }}
                        </span>
                      </td>
                      <td>
                        <div style="display: flex; gap: 8px;">
                          <button
                            class="btn-small btn-primary"
                            @click="downloadBackup(backup)"
                            :disabled="downloadingBackupId === backup.id"
                            title="Descargar backup"
                          >
                            <span v-if="downloadingBackupId === backup.id">⏳</span>
                            <span v-else>⬇️</span>
                            Descargar
                          </button>
                          <button
                            class="btn-small btn-danger"
                            @click="deleteBackup(backup)"
                            :disabled="deletingBackupId === backup.id"
                          >
                            <span v-if="deletingBackupId === backup.id">⏳</span>
                            <span v-else>🗑️</span>
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
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

    <!-- Modal: Empresas del Servidor -->
    <div v-if="showServerEmpresasModal" class="modal-overlay" @click="showServerEmpresasModal = false">
      <div class="modal-content empresas-modal" @click.stop style="max-width: 1400px; max-height: 90vh; overflow-y: auto;">
        <div class="modal-header">
          <div>
            <h2>Empresas del Servidor</h2>
            <p v-if="selectedServerForEmpresas" class="modal-subtitle">
              {{ servers.find(s => s.id === selectedServerForEmpresas)?.nombre }}
            </p>
          </div>
          <button class="modal-close" @click="showServerEmpresasModal = false">×</button>
        </div>
        <div v-if="loadingServerEmpresas" class="loading-state">
          <p>Cargando empresas...</p>
        </div>
        <div v-else-if="serverEmpresasList.length === 0" class="empty-state">
          <p>No hay empresas en este servidor</p>
        </div>
        <div v-else class="modal-body">
          <EmpresasTable
            :empresas="serverEmpresasList"
            :backup-menu-open="backupMenuOpen"
            @backup-click="handleBackupClick"
            @create-backup="hacerBackupEmpresa"
            @download-fbk="(id) => downloadBackupFromEmpresa(id, 'fbk')"
            @request-gdb="requestGdbDownload"
            @edit="editEmpresa"
            @close-backup-menu="backupMenuOpen = null"
          />
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showServerEmpresasModal = false">Cerrar</button>
        </div>
      </div>
    </div>

    <!-- Modal: Editar Empresa -->
    <div v-if="showEditEmpresaModal && editingEmpresa" class="modal-overlay" @click="showEditEmpresaModal = false">
      <div class="modal-content" @click.stop style="max-width: 600px;">
        <div class="modal-header">
          <h2>Editar Empresa</h2>
          <button class="modal-close" @click="showEditEmpresaModal = false">×</button>
        </div>
        <div class="form-container">
          <div class="form-group">
            <label>
              <span class="label-text">Código</span>
              <input
                v-model="editingEmpresa.codigo"
                type="text"
                class="form-input"
                disabled
              />
            </label>
          </div>
          <div class="form-group">
            <label>
              <span class="label-text">NIT</span>
              <input
                v-model="editingEmpresa.nit"
                type="text"
                class="form-input"
                placeholder="900.869.750-0"
              />
            </label>
          </div>
          <div class="form-group">
            <label>
              <span class="label-text">Razón Social</span>
              <input
                v-model="editingEmpresa.nombre"
                type="text"
                class="form-input"
                placeholder="Nombre de la empresa"
              />
            </label>
          </div>
          <div class="form-group">
            <label>
              <span class="label-text">Año Fiscal</span>
              <input
                v-model.number="editingEmpresa.anio_fiscal"
                type="number"
                class="form-input"
                min="2000"
                max="2100"
              />
            </label>
          </div>
          <div class="form-group">
            <label>
              <span class="label-text">Representante Legal</span>
              <input
                v-model="editingEmpresa.representante_legal"
                type="text"
                class="form-input"
                placeholder="Nombre completo del representante legal"
              />
            </label>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showEditEmpresaModal = false">Cancelar</button>
          <button class="btn-primary" @click="saveEmpresa">Guardar</button>
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

    <!-- Modal: Crear Usuario -->
    <div v-if="showCreateUser" class="modal-overlay" @click="showCreateUser = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Crear Nuevo Usuario</h2>
          <button class="modal-close" @click="showCreateUser = false">×</button>
        </div>
        <form @submit.prevent="createUser" class="modal-form">
          <div class="form-group">
            <label>Usuario *</label>
            <input v-model="newUser.username" type="text" required class="form-input" placeholder="nombre_usuario" />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="newUser.email" type="email" class="form-input" placeholder="usuario@ejemplo.com" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Nombre</label>
              <input v-model="newUser.first_name" type="text" class="form-input" placeholder="Nombre" />
            </div>
            <div class="form-group">
              <label>Apellido</label>
              <input v-model="newUser.last_name" type="text" class="form-input" placeholder="Apellido" />
            </div>
          </div>
          <div class="form-group">
            <label>Contraseña *</label>
            <input v-model="newUser.password" type="password" required class="form-input" placeholder="Mínimo 8 caracteres" />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newUser.is_active" />
              Usuario Activo
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newUser.is_staff" />
              Es Staff (acceso al admin)
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newUser.is_superuser" />
              Es Superusuario (todos los permisos)
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreateUser = false">Cancelar</button>
            <button type="submit" class="btn-primary">Crear Usuario</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Editar Usuario -->
    <div v-if="showEditUser && editingUser" class="modal-overlay" @click="showEditUser = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Editar Usuario: {{ editingUser.username }}</h2>
          <button class="modal-close" @click="showEditUser = false">×</button>
        </div>
        <form @submit.prevent="updateUser" class="modal-form">
          <div class="form-group">
            <label>Usuario *</label>
            <input v-model="editingUser.username" type="text" required class="form-input" />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="editingUser.email" type="email" class="form-input" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Nombre</label>
              <input v-model="editingUser.first_name" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label>Apellido</label>
              <input v-model="editingUser.last_name" type="text" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>Nueva Contraseña (opcional)</label>
            <input v-model="editingUser.password" type="password" class="form-input" placeholder="Dejar vacío para no cambiar" />
            <small>Dejar vacío si no quieres cambiar la contraseña</small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editingUser.is_active" />
              Usuario Activo
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editingUser.is_staff" />
              Es Staff (acceso al admin)
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editingUser.is_superuser" />
              Es Superusuario (todos los permisos)
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showEditUser = false">Cancelar</button>
            <button type="submit" class="btn-primary">Guardar Cambios</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Editar Consulta SQL -->
    <div v-if="showEditEmpresaSQL && editingEmpresaSQL" class="modal-overlay" @click="showEditEmpresaSQL = false">
      <div class="modal-content" style="max-width: 900px;" @click.stop>
        <div class="modal-header">
          <h2>Editar Consulta SQL: {{ editingEmpresaSQL.nombre }}</h2>
          <button class="modal-close" @click="showEditEmpresaSQL = false">×</button>
        </div>
        <div class="modal-form">
          <div class="form-group">
            <label>Consulta SQL Personalizada</label>
            <textarea 
              v-model="empresaSQLContent" 
              class="form-input" 
              rows="15"
              placeholder="SELECT TIPO_DOCUMENTO, FECHA, ARTICULO_CODIGO, ARTICULO_NOMBRE, CANTIDAD, PRECIO_UNITARIO FROM MOVIMIENTOS WHERE FECHA BETWEEN ? AND ?"
              style="font-family: 'Courier New', monospace; font-size: 0.9em;"
            ></textarea>
            <small>
              <strong>Nota:</strong> Esta consulta se usa para extraer datos de la base de datos. 
              Debe retornar los campos requeridos. Usa ? como placeholders para parámetros de fecha.
              Si está vacía, se usará la consulta por defecto del sistema.
            </small>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showEditEmpresaSQL = false">Cancelar</button>
            <button type="button" class="btn-primary" @click="saveEmpresaSQL">Guardar Consulta SQL</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Editar Configuración -->
    <div v-if="showEditEmpresaConfig && editingEmpresaConfig" class="modal-overlay" @click="showEditEmpresaConfig = false">
      <div class="modal-content" style="max-width: 900px;" @click.stop>
        <div class="modal-header">
          <h2>Editar Configuración: {{ editingEmpresaConfig.nombre }}</h2>
          <button class="modal-close" @click="showEditEmpresaConfig = false">×</button>
        </div>
        <div class="modal-form">
          <div class="form-group">
            <label>Configuración (JSON)</label>
            <textarea 
              v-model="empresaConfigContent" 
              class="form-input" 
              rows="20"
              placeholder='{"parametro1": "valor1", "parametro2": "valor2"}'
              style="font-family: 'Courier New', monospace; font-size: 0.9em;"
            ></textarea>
            <small>
              <strong>Nota:</strong> Esta configuración es un objeto JSON que permite parametrizar el comportamiento de la extracción de datos.
              Ejemplos de parámetros: filtros adicionales, mapeos de campos, configuraciones específicas por empresa.
              Debe ser un JSON válido.
            </small>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showEditEmpresaConfig = false">Cancelar</button>
            <button type="button" class="btn-primary" @click="saveEmpresaConfig">Guardar Configuración</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Crear API Key -->
    <div v-if="showCreateApiKey" class="modal-overlay" @click="showCreateApiKey = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Generar Nueva API Key</h2>
          <button class="modal-close" @click="showCreateApiKey = false">×</button>
        </div>
        <form @submit.prevent="createApiKey" class="modal-form">
          <div class="form-group">
            <label>NIT *</label>
            <select 
              v-model="newApiKey.nit" 
              required 
              class="form-input"
              @change="onNitSelected"
            >
              <option value="">Seleccionar NIT...</option>
              <option v-for="nitOption in uniqueNits" :key="nitOption.nit" :value="nitOption.nit">
                {{ nitOption.nit }} - {{ nitOption.nombre }}
              </option>
            </select>
            <small>Selecciona un NIT y el nombre se llenará automáticamente</small>
          </div>
          <div class="form-group">
            <label>Nombre del Cliente *</label>
            <input 
              v-model="newApiKey.nombre_cliente" 
              type="text" 
              required 
              class="form-input" 
              placeholder="Se llena automáticamente al seleccionar NIT"
            />
          </div>
          <div class="form-group">
            <label>Servidor (Opcional)</label>
            <select 
              v-model="newApiKey.servidor" 
              class="form-input"
            >
              <option :value="null">Todos los servidores (sin restricción)</option>
              <option v-for="server in servers" :key="server.id" :value="server.id">
                {{ server.nombre }}
              </option>
            </select>
            <small>Si seleccionas un servidor, la API Key solo tendrá acceso a empresas de ese servidor. Si no seleccionas, tendrá acceso a todas las empresas del NIT en todos los servidores.</small>
          </div>
          <div class="form-group">
            <label>Días de Validez</label>
            <input 
              v-model.number="newApiKey.dias_validez" 
              type="number" 
              min="1" 
              max="3650" 
              class="form-input" 
              placeholder="365"
            />
            <small>Número de días que la API Key será válida (por defecto: 365 días)</small>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreateApiKey = false">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="creatingApiKey || !newApiKey.nit || !newApiKey.nombre_cliente">
              <span v-if="creatingApiKey">⟳</span>
              <span v-else>Generar API Key</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Gestionar NITs de Calendario -->
    <div v-if="showManageCalendarioNits" class="modal-overlay" @click="showManageCalendarioNits = false">
      <div class="modal-content" @click.stop style="max-width: 900px; max-height: 90vh; overflow-y: auto;">
        <div class="modal-header">
          <div>
            <h2>Gestionar NITs de Calendario Tributario</h2>
            <p v-if="selectedApiKeyForCalendario" class="modal-subtitle">
              API Key: {{ apiKeys.find(k => k.id === selectedApiKeyForCalendario)?.nombre_cliente }}
            </p>
          </div>
          <button class="modal-close" @click="showManageCalendarioNits = false">×</button>
        </div>
        
        <div class="modal-body">
          <!-- Buscar RUTs -->
          <div class="form-group" style="margin-bottom: 2rem;">
            <label>Buscar RUTs por NIT o Razón Social</label>
            <div style="display: flex; gap: 0.5rem;">
              <input
                v-model="rutSearchQuery"
                type="text"
                class="form-input"
                placeholder="Ej: 900869750 o Nombre de empresa..."
                @keyup.enter="searchRuts"
              />
              <button
                class="btn-primary"
                @click="searchRuts"
                :disabled="searchingRuts || !rutSearchQuery.trim()"
              >
                <span v-if="searchingRuts">⟳</span>
                <span v-else>🔍</span>
                Buscar
              </button>
            </div>
            <small>Busca RUTs para asociarlos a esta API Key. Los NITs asociados aparecerán en el calendario tributario.</small>
          </div>

          <!-- Resultados de búsqueda -->
          <div v-if="rutSearchResults.length > 0" style="margin-bottom: 2rem;">
            <h3 style="margin-bottom: 1rem;">Resultados de Búsqueda</h3>
            <div style="max-height: 200px; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 0.5rem; padding: 0.5rem;">
              <label
                v-for="rut in rutSearchResults"
                :key="rut.id"
                style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; cursor: pointer; border-radius: 0.25rem;"
                :style="{ background: selectedRutNits.includes(rut.nit_normalizado) ? '#dbeafe' : 'transparent' }"
                @mouseenter="$event.currentTarget.style.background = '#f3f4f6'"
                @mouseleave="$event.currentTarget.style.background = selectedRutNits.includes(rut.nit_normalizado) ? '#dbeafe' : 'transparent'"
              >
                <input
                  type="checkbox"
                  :value="rut.nit_normalizado"
                  v-model="selectedRutNits"
                />
                <div style="flex: 1;">
                  <strong>{{ rut.razon_social }}</strong>
                  <div style="font-size: 0.875rem; color: #6b7280;">
                    NIT: {{ rut.nit }}-{{ rut.dv }} ({{ rut.nit_normalizado }})
                    <span v-if="rut.tipo_contribuyente" style="margin-left: 0.5rem;">
                      • {{ rut.tipo_contribuyente === 'persona_natural' ? 'Persona Natural' : 'Persona Jurídica' }}
                    </span>
                  </div>
                </div>
              </label>
            </div>
            <button
              v-if="selectedRutNits.length > 0"
              class="btn-primary"
              style="margin-top: 1rem;"
              @click="asociarNitsCalendario"
              :disabled="loadingCalendarioNits"
            >
              <span v-if="loadingCalendarioNits">⟳</span>
              <span v-else>+</span>
              Asociar {{ selectedRutNits.length }} NIT{{ selectedRutNits.length > 1 ? 's' : '' }}
            </button>
          </div>

          <!-- NITs asociados -->
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
              <h3>NITs Asociados ({{ calendarioNits.length }})</h3>
              <button
                class="btn-secondary"
                @click="loadCalendarioNits"
                :disabled="loadingCalendarioNits"
              >
                <span v-if="loadingCalendarioNits">⟳</span>
                <span v-else>↻</span>
                Actualizar
              </button>
            </div>
            
            <div v-if="loadingCalendarioNits" class="loading-state">
              <p>Cargando NITs...</p>
            </div>
            
            <div v-else-if="calendarioNits.length === 0" class="empty-state">
              <p>No hay NITs asociados para calendario tributario</p>
            </div>
            
            <div v-else style="border: 1px solid #e5e7eb; border-radius: 0.5rem; overflow: hidden;">
              <table style="width: 100%; border-collapse: collapse;">
                <thead style="background: #f9fafb;">
                  <tr>
                    <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb;">NIT</th>
                    <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb;">Razón Social</th>
                    <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb;">Tipo</th>
                    <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb;">Fecha</th>
                    <th style="padding: 0.75rem; text-align: center; border-bottom: 1px solid #e5e7eb;">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="nit in calendarioNits"
                    :key="nit.id"
                    style="border-bottom: 1px solid #e5e7eb;"
                  >
                    <td style="padding: 0.75rem;">
                      <code>{{ nit.nit_normalizado }}</code>
                    </td>
                    <td style="padding: 0.75rem;">
                      {{ nit.rut_razon_social || 'N/A' }}
                    </td>
                    <td style="padding: 0.75rem;">
                      <span v-if="nit.rut_tipo_contribuyente" class="badge">
                        {{ nit.rut_tipo_contribuyente === 'persona_natural' ? 'PN' : 'PJ' }}
                      </span>
                      <span v-else class="text-muted">-</span>
                    </td>
                    <td style="padding: 0.75rem; font-size: 0.875rem; color: #6b7280;">
                      {{ formatDate(nit.fecha_asociacion) }}
                    </td>
                    <td style="padding: 0.75rem; text-align: center;">
                      <button
                        class="btn-tiny btn-danger"
                        @click="eliminarNitCalendario(nit.id)"
                        title="Eliminar"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        
        <div class="modal-actions">
          <button class="btn-secondary" @click="showManageCalendarioNits = false">Cerrar</button>
        </div>
      </div>
    </div>

    <!-- Modal: Crear Dominio -->
    <div v-if="showCreateDominio" class="modal-overlay" @click="showCreateDominio = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Crear Nuevo Dominio</h2>
          <button class="modal-close" @click="showCreateDominio = false">×</button>
        </div>
        <form @submit.prevent="createDominio" class="modal-form">
          <div class="form-group">
            <label>Dominio *</label>
            <input 
              v-model="newDominio.dominio" 
              type="text" 
              required 
              class="form-input" 
              placeholder="pepito.ecommerce.miapp.com"
            />
            <small>Dominio completo (ej: pepito.ecommerce.miapp.com)</small>
          </div>
          <div class="form-group">
            <label>NIT *</label>
            <select 
              v-model="newDominio.nit" 
              required 
              class="form-input"
              @change="onDominioNitSelected"
            >
              <option value="">Seleccionar NIT...</option>
              <option v-for="nitOption in uniqueNits" :key="nitOption.nit" :value="nitOption.nit">
                {{ nitOption.nit }} - {{ nitOption.nombre }}
              </option>
            </select>
            <small>Selecciona un NIT. El sistema buscará automáticamente la empresa con el año fiscal más reciente.</small>
          </div>
          <div class="form-group">
            <label>Servidor (Opcional)</label>
            <select 
              v-model="newDominio.servidor" 
              class="form-input"
            >
              <option :value="null">Todos los servidores (sin restricción)</option>
              <option v-for="server in servers" :key="server.id" :value="server.id">
                {{ server.nombre }}
              </option>
            </select>
            <small>Si seleccionas un servidor, el dominio solo resolverá a empresas de ese servidor. Si no seleccionas, buscará en todos los servidores.</small>
          </div>
          <div class="form-group">
            <label>Modo *</label>
            <select v-model="newDominio.modo" required class="form-input">
              <option value="ecommerce">E-commerce público</option>
              <option value="autopago">Autopago / Retail</option>
              <option value="pro">Profesional</option>
            </select>
            <small>Modo principal de este dominio</small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newDominio.activo" />
              Dominio Activo
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreateDominio = false">Cancelar</button>
            <button type="submit" class="btn-primary">Crear Dominio</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Editar Dominio -->
    <div v-if="showEditDominio && editingDominio" class="modal-overlay" @click="showEditDominio = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Editar Dominio: {{ editingDominio.dominio }}</h2>
          <button class="modal-close" @click="showEditDominio = false">×</button>
        </div>
        <form @submit.prevent="updateDominio" class="modal-form">
          <div class="form-group">
            <label>Dominio *</label>
            <input 
              v-model="editingDominio.dominio" 
              type="text" 
              required 
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>NIT</label>
            <input 
              v-model="editingDominio.nit" 
              type="text" 
              class="form-input"
              placeholder="Sin puntos ni guiones"
            />
            <small>Si cambias el NIT, el sistema buscará automáticamente la empresa con el año fiscal más reciente.</small>
          </div>
          <div class="form-group">
            <label>Servidor (Opcional)</label>
            <select 
              v-model="editingDominio.servidor" 
              class="form-input"
            >
              <option :value="null">Todos los servidores (sin restricción)</option>
              <option v-for="server in servers" :key="server.id" :value="server.id">
                {{ server.nombre }}
              </option>
            </select>
            <small>Si seleccionas un servidor, el dominio solo resolverá a empresas de ese servidor. Si no seleccionas, buscará en todos los servidores.</small>
          </div>
          <div class="form-group">
            <label>Modo *</label>
            <select v-model="editingDominio.modo" required class="form-input">
              <option value="ecommerce">E-commerce público</option>
              <option value="autopago">Autopago / Retail</option>
              <option value="pro">Profesional</option>
            </select>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editingDominio.activo" />
              Dominio Activo
            </label>
          </div>
          <div v-if="editingDominio.empresa_servidor_nombre" class="form-group" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">
            <small>
              <strong>Empresa asociada:</strong> {{ editingDominio.empresa_servidor_nombre }} ({{ editingDominio.empresa_servidor_nit }})<br>
              <strong>Año fiscal:</strong> {{ editingDominio.anio_fiscal || 'N/A' }}
            </small>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showEditDominio = false">Cancelar</button>
            <button type="submit" class="btn-primary">Guardar Cambios</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Crear Pasarela -->
    <div v-if="showCreatePasarela" class="modal-overlay" @click="showCreatePasarela = false">
      <div class="modal-content" style="max-width: 900px;" @click.stop>
        <div class="modal-header">
          <h2>Crear Nueva Pasarela de Pago</h2>
          <button class="modal-close" @click="showCreatePasarela = false">×</button>
        </div>
        <form @submit.prevent="createPasarela" class="modal-form">
          <div class="form-group">
            <label>Código *</label>
            <input 
              v-model="newPasarela.codigo" 
              type="text" 
              required 
              class="form-input" 
              placeholder="credibanco"
            />
            <small>Código único de la pasarela (ej: credibanco, payu, etc.)</small>
          </div>
          <div class="form-group">
            <label>Nombre *</label>
            <input 
              v-model="newPasarela.nombre" 
              type="text" 
              required 
              class="form-input" 
              placeholder="Credibanco"
            />
            <small>Nombre descriptivo de la pasarela</small>
          </div>
          <div class="form-group">
            <label>Configuración (JSON)</label>
            <textarea 
              v-model="pasarelaConfigContent" 
              class="form-input" 
              rows="15"
              placeholder='{"url_base": "https://api.credibanco.com", "endpoint_pago": "/pagos", ...}'
              style="font-family: 'Courier New', monospace; font-size: 0.9em;"
            ></textarea>
            <small>
              <strong>Nota:</strong> Configuración específica de la pasarela en formato JSON.
              Puede incluir URLs, endpoints, campos adicionales, etc. Debe ser un JSON válido.
            </small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newPasarela.activa" />
              Pasarela Activa
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreatePasarela = false">Cancelar</button>
            <button type="submit" class="btn-primary">Crear Pasarela</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Editar Pasarela -->
    <div v-if="showEditPasarela && editingPasarela" class="modal-overlay" @click="showEditPasarela = false">
      <div class="modal-content" style="max-width: 900px;" @click.stop>
        <div class="modal-header">
          <h2>Editar Pasarela: {{ editingPasarela.nombre }}</h2>
          <button class="modal-close" @click="showEditPasarela = false">×</button>
        </div>
        <form @submit.prevent="updatePasarela" class="modal-form">
          <div class="form-group">
            <label>Código *</label>
            <input 
              v-model="editingPasarela.codigo" 
              type="text" 
              required 
              class="form-input"
              readonly
            />
            <small>El código no se puede modificar</small>
          </div>
          <div class="form-group">
            <label>Nombre *</label>
            <input 
              v-model="editingPasarela.nombre" 
              type="text" 
              required 
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>Configuración (JSON)</label>
            <textarea 
              v-model="pasarelaConfigContent" 
              class="form-input" 
              rows="15"
              style="font-family: 'Courier New', monospace; font-size: 0.9em;"
            ></textarea>
            <small>
              <strong>Nota:</strong> Configuración específica de la pasarela en formato JSON.
              Debe ser un JSON válido.
            </small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editingPasarela.activa" />
              Pasarela Activa
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showEditPasarela = false">Cancelar</button>
            <button type="submit" class="btn-primary">Guardar Cambios</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Crear Permiso -->
    <div v-if="showCreatePermiso" class="modal-overlay" @click="showCreatePermiso = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Crear Permiso Usuario-Empresa</h2>
          <button class="modal-close" @click="showCreatePermiso = false">×</button>
        </div>
        <form @submit.prevent="createPermiso" class="modal-form">
          <div class="form-group">
            <label>Usuario *</label>
            <select v-model.number="newPermiso.usuario" required class="form-input">
              <option :value="null">Seleccionar usuario...</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.username }} {{ user.email ? `(${user.email})` : '' }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>Empresa *</label>
            <select v-model.number="newPermiso.empresa_servidor" required class="form-input">
              <option :value="null">Seleccionar empresa...</option>
              <option v-for="empresa in empresas" :key="empresa.id" :value="empresa.id">
                {{ empresa.nombre }} ({{ empresa.nit }}) - {{ empresa.anio_fiscal }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newPermiso.puede_ver" />
              Puede Ver
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="newPermiso.puede_editar" />
              Puede Editar
            </label>
          </div>
          <div class="form-group">
            <label>Template Preferido</label>
            <select v-model="newPermiso.preferred_template" class="form-input">
              <option value="pro">Profesional</option>
              <option value="retail">Retail / Autopago</option>
              <option value="restaurant">Restaurante</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreatePermiso = false">Cancelar</button>
            <button type="submit" class="btn-primary">Crear Permiso</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Editar Permiso -->
    <div v-if="showEditPermiso && editingPermiso" class="modal-overlay" @click="showEditPermiso = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Editar Permiso</h2>
          <button class="modal-close" @click="showEditPermiso = false">×</button>
        </div>
        <form @submit.prevent="updatePermiso" class="modal-form">
          <div class="form-group" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">
            <small>
              <strong>Usuario:</strong> {{ editingPermiso.usuario_username }}<br>
              <strong>Empresa:</strong> {{ editingPermiso.empresa_nombre }} ({{ editingPermiso.empresa_nit }})
            </small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editingPermiso.puede_ver" />
              Puede Ver
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="editingPermiso.puede_editar" />
              Puede Editar
            </label>
          </div>
          <div class="form-group">
            <label>Template Preferido</label>
            <select v-model="editingPermiso.preferred_template" class="form-input">
              <option value="pro">Profesional</option>
              <option value="retail">Retail / Autopago</option>
              <option value="restaurant">Restaurante</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showEditPermiso = false">Cancelar</button>
            <button type="submit" class="btn-primary">Guardar Cambios</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Crear Tenant Profile -->
    <div v-if="showCreateTenantProfile" class="modal-overlay" @click="showCreateTenantProfile = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Crear Tenant Profile</h2>
          <button class="modal-close" @click="showCreateTenantProfile = false">×</button>
        </div>
        <form @submit.prevent="createTenantProfile" class="modal-form">
          <div class="form-group">
            <label>Usuario *</label>
            <select v-model.number="newTenantProfile.user" required class="form-input">
              <option :value="null">Seleccionar usuario...</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.username }} {{ user.email ? `(${user.email})` : '' }}
              </option>
            </select>
            <small>El usuario no debe tener ya un tenant profile</small>
          </div>
          <div class="form-group">
            <label>Subdomain *</label>
            <input 
              v-model="newTenantProfile.subdomain" 
              type="text" 
              required 
              class="form-input" 
              placeholder="empresa"
            />
            <small>Subdomain único para este usuario (ej: empresa, cliente, etc.)</small>
          </div>
          <div class="form-group">
            <label>Template Preferido</label>
            <select v-model="newTenantProfile.preferred_template" class="form-input">
              <option value="pro">Profesional</option>
              <option value="retail">Retail / Autopago</option>
              <option value="restaurant">Restaurante</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showCreateTenantProfile = false">Cancelar</button>
            <button type="submit" class="btn-primary">Crear Tenant Profile</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Editar Tenant Profile -->
    <div v-if="showEditTenantProfile && editingTenantProfile" class="modal-overlay" @click="showEditTenantProfile = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Editar Tenant Profile</h2>
          <button class="modal-close" @click="showEditTenantProfile = false">×</button>
        </div>
        <form @submit.prevent="updateTenantProfile" class="modal-form">
          <div class="form-group" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">
            <small>
              <strong>Usuario:</strong> {{ editingTenantProfile.user_username }}<br>
              <strong>Email:</strong> {{ editingTenantProfile.user_email || 'N/A' }}
            </small>
          </div>
          <div class="form-group">
            <label>Subdomain *</label>
            <input 
              v-model="editingTenantProfile.subdomain" 
              type="text" 
              required 
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>Template Preferido</label>
            <select v-model="editingTenantProfile.preferred_template" class="form-input">
              <option value="pro">Profesional</option>
              <option value="retail">Retail / Autopago</option>
              <option value="restaurant">Restaurante</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showEditTenantProfile = false">Cancelar</button>
            <button type="submit" class="btn-primary">Guardar Cambios</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Subir RUT PDF o ZIP -->
    <div v-if="showUploadRUT" class="modal-overlay" @click="showUploadRUT = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Subir RUT PDF o ZIP</h2>
          <button class="modal-close" @click="showUploadRUT = false">×</button>
        </div>
        <form @submit.prevent="uploadRUTPDF" class="modal-form">
          <div class="form-group">
            <label>Archivo PDF del RUT (Individual) *</label>
            <input 
              type="file" 
              accept=".pdf"
              @change="onRUTFileSelected"
              :required="!selectedRUTZipFile"
              class="form-input"
            />
            <small>
              <strong>Nota:</strong> El sistema detectará automáticamente el NIT del PDF.
              Si el PDF no contiene el NIT o quieres especificarlo manualmente, puedes ingresarlo abajo.
            </small>
          </div>
          <div style="text-align: center; margin: 20px 0; color: #666;">
            <strong>O</strong>
          </div>
          <div class="form-group">
            <label>Archivo ZIP con múltiples PDFs (Carga Masiva) *</label>
            <input 
              type="file" 
              accept=".zip"
              @change="onRUTZipSelected"
              :required="!selectedRUTFile"
              class="form-input"
            />
            <small>
              <strong>Nota:</strong> El ZIP debe contener archivos PDF de RUT.
              Los RUTs que no tengan empresas asociadas serán omitidos y se generará un reporte TXT.
            </small>
          </div>
          <div class="form-group">
            <label>NIT (Opcional - Solo si el PDF no lo contiene)</label>
            <input 
              v-model="rutNitManual" 
              type="text" 
              class="form-input" 
              placeholder="900.869.750-0 o 9008697500"
            />
            <small>
              Puedes ingresar el NIT con o sin formato (puntos y guiones).
              El sistema lo normalizará automáticamente.
            </small>
          </div>
          <div class="form-group" style="padding: 15px; background: #e3f2fd; border-radius: 5px; border-left: 4px solid #2196F3;">
            <strong>💡 Información:</strong>
            <ul style="margin: 10px 0 0 20px; text-align: left;">
              <li>El sistema detectará automáticamente el NIT del PDF</li>
              <li>Si ya existe un RUT para ese NIT, se actualizará</li>
              <li>El RUT se asociará a todas las empresas con el mismo NIT</li>
              <li>El PDF anterior se reemplazará si existe</li>
            </ul>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showUploadRUT = false">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="uploadingRUT || (!selectedRUTFile && !selectedRUTZipFile)">
              <span v-if="uploadingRUT">⟳</span>
              <span v-else>{{ selectedRUTZipFile ? '📦 Subir y Procesar ZIP' : '📄 Subir y Procesar PDF' }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Detalles RUT -->
    <div v-if="showRUTDetails && selectedRUT" class="modal-overlay" @click="showRUTDetails = false">
      <div class="modal-content" style="max-width: 1000px; max-height: 90vh; overflow-y: auto;" @click.stop>
        <div class="modal-header">
          <h2>Detalles del RUT: {{ selectedRUT.razon_social }}</h2>
          <button class="modal-close" @click="showRUTDetails = false">×</button>
        </div>
        <div class="modal-form" style="padding: 20px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
              <h3 style="margin-bottom: 15px; color: #333;">Identificación</h3>
              <div class="detail-item">
                <strong>NIT:</strong> {{ selectedRUT.nit }}-{{ selectedRUT.dv }}<br>
                <small style="color: #666;">Normalizado: {{ selectedRUT.nit_normalizado }}</small>
              </div>
              <div class="detail-item">
                <strong>Razón Social:</strong> {{ selectedRUT.razon_social }}
              </div>
              <div class="detail-item" v-if="selectedRUT.nombre_comercial">
                <strong>Nombre Comercial:</strong> {{ selectedRUT.nombre_comercial }}
              </div>
              <div class="detail-item" v-if="selectedRUT.sigla">
                <strong>Sigla:</strong> {{ selectedRUT.sigla }}
              </div>
              <div class="detail-item">
                <strong>Tipo Contribuyente:</strong> {{ selectedRUT.tipo_contribuyente === 'persona_juridica' ? 'Persona Jurídica' : 'Persona Natural' }}
              </div>
            </div>
            
            <div>
              <h3 style="margin-bottom: 15px; color: #333;">Ubicación</h3>
              <div class="detail-item">
                <strong>Dirección:</strong> {{ selectedRUT.direccion_principal }}
              </div>
              <div class="detail-item">
                <strong>Ciudad:</strong> {{ selectedRUT.ciudad_nombre }} ({{ selectedRUT.ciudad_codigo }})
              </div>
              <div class="detail-item">
                <strong>Departamento:</strong> {{ selectedRUT.departamento_nombre }} ({{ selectedRUT.departamento_codigo }})
              </div>
              <div class="detail-item" v-if="selectedRUT.telefono_1">
                <strong>Teléfono:</strong> {{ selectedRUT.telefono_1 }}
              </div>
              <div class="detail-item" v-if="selectedRUT.email">
                <strong>Email:</strong> {{ selectedRUT.email }}
              </div>
            </div>
          </div>
          
          <div style="margin-top: 30px;">
            <h3 style="margin-bottom: 15px; color: #333;">Empresas Asociadas</h3>
            <div v-if="selectedRUT.empresas_asociadas && selectedRUT.empresas_asociadas.length > 0" class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>NIT</th>
                    <th>Año Fiscal</th>
                    <th>Servidor</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="empresa in selectedRUT.empresas_asociadas" :key="empresa.id">
                    <td><strong>{{ empresa.nombre }}</strong></td>
                    <td>{{ empresa.nit }}</td>
                    <td>{{ empresa.anio_fiscal }}</td>
                    <td>{{ empresa.servidor || '-' }}</td>
                    <td>
                      <span class="status-badge" :class="empresa.estado === 'ACTIVO' ? 'status-active' : 'status-inactive'">
                        {{ empresa.estado || 'ACTIVO' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else style="padding: 20px; text-align: center; color: #999;">
              No hay empresas asociadas con este NIT
            </div>
          </div>
          
          <!-- Actividades Económicas CIIU -->
          <div style="margin-top: 30px;">
            <h3 style="margin-bottom: 15px; color: #333;">Actividades Económicas (CIIU)</h3>
            
            <!-- Actividad Principal -->
            <div v-if="selectedRUT.actividad_principal_info" style="margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px; border-left: 4px solid #4CAF50;">
              <strong style="color: #4CAF50;">📌 Actividad Principal:</strong>
              <div style="margin-top: 10px;">
                <div><strong>Código:</strong> <code>{{ selectedRUT.actividad_principal_info.codigo }}</code></div>
                <div v-if="selectedRUT.actividad_principal_info.descripcion">
                  <strong>Descripción:</strong> {{ selectedRUT.actividad_principal_info.descripcion }}
                </div>
                <div v-if="selectedRUT.actividad_principal_info.titulo">
                  <strong>Título:</strong> {{ selectedRUT.actividad_principal_info.titulo }}
                </div>
                <div v-if="selectedRUT.actividad_principal_info.division">
                  <strong>División:</strong> {{ selectedRUT.actividad_principal_info.division }}
                </div>
                <div v-if="selectedRUT.actividad_principal_info.grupo">
                  <strong>Grupo:</strong> {{ selectedRUT.actividad_principal_info.grupo }}
                </div>
              </div>
            </div>
            
            <!-- Actividad Secundaria -->
            <div v-if="selectedRUT.actividad_secundaria_info" style="margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px; border-left: 4px solid #2196F3;">
              <strong style="color: #2196F3;">📋 Actividad Secundaria:</strong>
              <div style="margin-top: 10px;">
                <div><strong>Código:</strong> <code>{{ selectedRUT.actividad_secundaria_info.codigo }}</code></div>
                <div v-if="selectedRUT.actividad_secundaria_info.descripcion">
                  <strong>Descripción:</strong> {{ selectedRUT.actividad_secundaria_info.descripcion }}
                </div>
                <div v-if="selectedRUT.actividad_secundaria_info.titulo">
                  <strong>Título:</strong> {{ selectedRUT.actividad_secundaria_info.titulo }}
                </div>
              </div>
            </div>
            
            <!-- Otras Actividades -->
            <div v-if="selectedRUT.otras_actividades_info && selectedRUT.otras_actividades_info.length > 0" style="margin-bottom: 20px;">
              <strong style="color: #FF9800;">📚 Otras Actividades ({{ selectedRUT.otras_actividades_info.length }}):</strong>
              <div style="margin-top: 10px; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px;">
                <div 
                  v-for="(actividad, idx) in selectedRUT.otras_actividades_info" 
                  :key="idx"
                  style="padding: 10px; background: #fff; border-radius: 5px; border: 1px solid #ddd;"
                >
                  <div><strong>Código:</strong> <code>{{ actividad.codigo }}</code></div>
                  <div v-if="actividad.descripcion" style="margin-top: 5px; font-size: 0.9em; color: #666;">
                    {{ actividad.descripcion }}
                  </div>
                  <div v-if="actividad.titulo" style="margin-top: 5px; font-size: 0.9em; color: #666;">
                    {{ actividad.titulo }}
                  </div>
                </div>
              </div>
            </div>
            
            <div v-if="!selectedRUT.actividad_principal_info && !selectedRUT.actividad_secundaria_info && (!selectedRUT.otras_actividades_info || selectedRUT.otras_actividades_info.length === 0)" style="padding: 20px; text-align: center; color: #999;">
              No hay actividades económicas registradas
            </div>
          </div>
          
          <div style="margin-top: 30px; text-align: center;">
            <a 
              v-if="selectedRUT.archivo_pdf_url" 
              :href="selectedRUT.archivo_pdf_url" 
              target="_blank"
              class="btn-primary"
            >
              📄 Ver PDF Original
            </a>
          </div>
          
          <div class="modal-actions" style="margin-top: 30px;">
            <button type="button" class="btn-secondary" @click="showRUTDetails = false">Cerrar</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Subir Calendario Tributario Excel -->
    <div v-if="showUploadCalendario" class="modal-overlay" @click="showUploadCalendario = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Cargar Calendario Tributario</h2>
          <button class="modal-close" @click="showUploadCalendario = false">×</button>
        </div>
        <form @submit.prevent="uploadCalendarioExcel" class="modal-form">
          <div class="form-group">
            <label>Archivo Excel del Calendario *</label>
            <input 
              type="file" 
              accept=".xlsx,.xls"
              @change="onCalendarioFileSelected"
              required
              class="form-input"
            />
            <small>
              <strong>Formato esperado:</strong> Excel con hoja "CALENDARIO_TRIBUTARIO" con columnas:
              tax_code, expirations_digits, third_type_code, regiment_type_code, date, description
            </small>
          </div>
          <div class="form-group" style="padding: 15px; background: #e3f2fd; border-radius: 5px; border-left: 4px solid #2196F3;">
            <strong>💡 Información:</strong>
            <ul style="margin: 10px 0 0 20px; text-align: left;">
              <li>El sistema detectará automáticamente las empresas asociadas por NIT</li>
              <li>Si ya existe una vigencia con los mismos parámetros, se actualizará</li>
              <li>Se crearán automáticamente los impuestos, tipos de tercero y regímenes si no existen</li>
              <li>El formato de fecha debe ser DD/MM/YYYY o YYYY-MM-DD</li>
            </ul>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showUploadCalendario = false">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="uploadingCalendario || !selectedCalendarioFile">
              <span v-if="uploadingCalendario">⟳</span>
              <span v-else>📅 Cargar y Procesar Excel</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, computed, onMounted } from 'vue'
import { useRuntimeConfig } from '#app'
import { useAuthState } from '~/composables/useAuthState'
import ServidorCard from './components/ServidorCard.vue'
import ToastContainer from './components/ToastContainer.vue'
import EmpresasTable from './components/EmpresasTable.vue'
import CalendarioTributarioTable from './components/CalendarioTributarioTable.vue'
import UsuariosTable from './components/UsuariosTable.vue'
import ApiKeysTable from './components/ApiKeysTable.vue'
import Tabs from './components/Tabs.vue'
import SearchBar from './components/SearchBar.vue'
import Pagination from './components/Pagination.vue'
import { usePagination } from './composables/usePagination'
import { exportToCSV, exportToExcel } from './utils/exporters'
import { useToast } from './composables/useToast'

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
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>`
  },
  { 
    id: 'dominios', 
    name: '5. Dominios',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/>
      <line x1="2" y1="12" x2="22" y2="12"/>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>`
  },
  { 
    id: 'pasarelas', 
    name: '6. Pasarelas',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
      <line x1="1" y1="10" x2="23" y2="10"/>
    </svg>`
  },
  { 
    id: 'ruts', 
    name: '9. RUTs',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="2" y="3" width="20" height="18" rx="2"/>
      <line x1="8" y1="21" x2="16" y2="21"/>
      <line x1="12" y1="17" x2="12" y2="21"/>
      <path d="M7 8h10M7 12h10M7 16h6"/>
    </svg>`
  },
  { 
    id: 'calendario-tributario', 
    name: '10. Calendario Tributario',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
      <line x1="16" y1="2" x2="16" y2="6"/>
      <line x1="8" y1="2" x2="8" y2="6"/>
      <line x1="3" y1="10" x2="21" y2="10"/>
      <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01"/>
    </svg>`
  },
  { 
    id: 'backups-s3', 
    name: '11. Backups S3',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M4 4h16v6H4z"/>
      <path d="M4 14h16v6H4z"/>
      <path d="M8 8h.01M12 8h.01M16 8h.01"/>
      <path d="M8 18h.01M12 18h.01M16 18h.01"/>
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
const users = ref<any[]>([])
const loadingUsers = ref(false)
const userSearch = ref('')
const showCreateUser = ref(false)
const showEditUser = ref(false)
const userActiveTab = ref<'usuarios' | 'permisos' | 'tenant-profiles'>('usuarios')
const openUserMenu = ref<number | null>(null) // ID del usuario cuyo menú está abierto
const editingUser = ref<any>(null)
const showEditEmpresaSQL = ref(false)
const showEditEmpresaConfig = ref(false)
const editingEmpresaSQL = ref<any>(null)
const editingEmpresaConfig = ref<any>(null)
const empresaSQLContent = ref('')
const empresaConfigContent = ref('')
const dominios = ref<any[]>([])
const loadingDominios = ref(false)
const showCreateDominio = ref(false)
const showEditDominio = ref(false)
const editingDominio = ref<any>(null)
const newDominio = ref({
  dominio: '',
  nit: '',
  servidor: null,
  modo: 'ecommerce',
  activo: true
})
const pasarelas = ref<any[]>([])
const loadingPasarelas = ref(false)
const showCreatePasarela = ref(false)
const showEditPasarela = ref(false)
const editingPasarela = ref<any>(null)
const newPasarela = ref({
  codigo: '',
  nombre: '',
  activa: true,
  configuracion: {}
})
const pasarelaConfigContent = ref('{}')
const permisosUsuarios = ref<any[]>([])
const loadingPermisos = ref(false)
const showCreatePermiso = ref(false)
const showEditPermiso = ref(false)
const editingPermiso = ref<any>(null)
const newPermiso = ref({
  usuario: null,
  empresa_servidor: null,
  puede_ver: true,
  puede_editar: false,
  preferred_template: 'pro'
})
const tenantProfiles = ref<any[]>([])
const loadingTenantProfiles = ref(false)
const showCreateTenantProfile = ref(false)
const showEditTenantProfile = ref(false)
const editingTenantProfile = ref<any>(null)
const newTenantProfile = ref({
  user: null,
  subdomain: '',
  preferred_template: 'pro'
})
const ruts = ref<any[]>([])
const loadingRuts = ref(false)
const showUploadRUT = ref(false)
const uploadingRUT = ref(false)
const selectedRUTFile = ref<File | null>(null)
const selectedRUTZipFile = ref<File | null>(null)
const rutReporteTxt = ref<string | null>(null)

// Calendario Tributario
const vigenciasTributarias = ref<any[]>([])
const loadingCalendario = ref(false)
const showUploadCalendario = ref(false)
const uploadingCalendario = ref(false)
const selectedCalendarioFile = ref<File | null>(null)
// Filtros y ordenamiento para Calendario Tributario
const calendarioSortBy = ref<string>('fecha_limite')
const calendarioSortOrder = ref<'asc' | 'desc'>('asc')
const calendarioFilters = ref({
  impuesto: '',
  tipo_tercero: '',
  tipo_regimen: '',
  digitos_nit: ''
})
const calendarioItemsPerPage = ref(50)
const calendarioPagination = usePagination(computed(() => filteredAndSortedVigencias.value), calendarioItemsPerPage.value)
const paginatedVigencias = computed(() => {
  // Resetear paginación si cambian los filtros
  if (calendarioPagination.currentPage.value > calendarioPagination.totalPages.value) {
    calendarioPagination.reset()
  }
  return calendarioPagination.paginatedItems.value
})
const rutNitManual = ref('')
const selectedRUT = ref<any>(null)
const showRUTDetails = ref(false)

// Backups S3
const s3Configs = ref<any[]>([])
const activeS3Config = ref<any | null>(null)
const loadingS3Config = ref(false)
const savingS3Config = ref(false)

const backupsS3 = ref<any[]>([])
const loadingBackupsS3 = ref(false)
const selectedBackupEmpresaId = ref<number | null>(null)
const backupStats = ref<any | null>(null)
const triggeringBackup = ref(false)
const deletingBackupId = ref<number | null>(null)
const downloadingBackupId = ref<number | null>(null)
const showServerEmpresasModal = ref(false)
const selectedServerForEmpresas = ref<number | null>(null)
const serverEmpresasList = ref<any[]>([])
const loadingServerEmpresas = ref(false)
const showEditEmpresaModal = ref(false)
const editingEmpresa = ref<any>(null)
const empresaMenuOpen = ref<number | null>(null)
const backupMenuOpen = ref<number | null>(null)
const empresasItemsPerPage = ref(25)
const empresasPagination = usePagination(computed(() => serverEmpresasList.value), empresasItemsPerPage.value)
const paginatedEmpresasList = computed(() => empresasPagination.paginatedItems.value)

const scanningServer = ref<number | null>(null)
const activeScanTasks = ref<Record<number, string>>({}) // servidor_id -> task_id
const openServerMenu = ref<number | null>(null) // ID del servidor cuyo menú está abierto
const showCreateServer = ref(false)
const showEditServer = ref(false)
const editingServer = ref<Servidor | null>(null)
const showCreateVpn = ref(false)
const showCreateApiKey = ref(false)
const showManageCalendarioNits = ref(false)
const selectedApiKeyForCalendario = ref<number | null>(null)
const calendarioNits = ref<any[]>([])
const loadingCalendarioNits = ref(false)
const searchingRuts = ref(false)
const rutSearchQuery = ref('')
const rutSearchResults = ref<any[]>([])
const selectedRutNits = ref<string[]>([])
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

const newUser = ref({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  is_active: true,
  is_staff: false,
  is_superuser: false
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

const usuariosItemsPerPage = ref(10)
const filteredUsers = computed(() => {
  if (!userSearch.value) return users.value
  const search = userSearch.value.toLowerCase()
  return users.value.filter(u => 
    u.username.toLowerCase().includes(search) ||
    (u.email || '').toLowerCase().includes(search) ||
    (u.first_name || '').toLowerCase().includes(search) ||
    (u.last_name || '').toLowerCase().includes(search)
  )
})
const usuariosPagination = usePagination(computed(() => filteredUsers.value), usuariosItemsPerPage.value)

// Computed para Calendario Tributario: valores únicos para filtros
const uniqueImpuestos = computed(() => {
  const impuestos = new Set<string>()
  vigenciasTributarias.value.forEach(v => {
    if (v.impuesto?.codigo) impuestos.add(v.impuesto.codigo)
  })
  return Array.from(impuestos).sort()
})

const uniqueTiposTercero = computed(() => {
  const tipos = new Set<string>()
  vigenciasTributarias.value.forEach(v => {
    const tipo = v.tipo_tercero?.codigo || 'TODOS'
    tipos.add(tipo)
  })
  return Array.from(tipos).sort()
})

const uniqueRegimenes = computed(() => {
  const regimenes = new Set<string>()
  vigenciasTributarias.value.forEach(v => {
    const regimen = v.tipo_regimen?.codigo || 'TODOS'
    regimenes.add(regimen)
  })
  return Array.from(regimenes).sort()
})

// Computed para filtrar y ordenar vigencias tributarias
const filteredAndSortedVigencias = computed(() => {
  let filtered = [...vigenciasTributarias.value]
  
  // Aplicar filtros
  if (calendarioFilters.value.impuesto) {
    filtered = filtered.filter(v => v.impuesto?.codigo === calendarioFilters.value.impuesto)
  }
  if (calendarioFilters.value.tipo_tercero) {
    const tipo = calendarioFilters.value.tipo_tercero === 'TODOS' ? null : calendarioFilters.value.tipo_tercero
    filtered = filtered.filter(v => (v.tipo_tercero?.codigo || 'TODOS') === (tipo || 'TODOS'))
  }
  if (calendarioFilters.value.tipo_regimen) {
    const regimen = calendarioFilters.value.tipo_regimen === 'TODOS' ? null : calendarioFilters.value.tipo_regimen
    filtered = filtered.filter(v => (v.tipo_regimen?.codigo || 'TODOS') === (regimen || 'TODOS'))
  }
  if (calendarioFilters.value.digitos_nit) {
    filtered = filtered.filter(v => (v.digitos_nit || '').includes(calendarioFilters.value.digitos_nit))
  }
  
  // Aplicar ordenamiento
  filtered.sort((a, b) => {
    let aVal: any, bVal: any
    
    switch (calendarioSortBy.value) {
      case 'impuesto':
        aVal = a.impuesto?.codigo || ''
        bVal = b.impuesto?.codigo || ''
        break
      case 'digitos_nit':
        aVal = a.digitos_nit || 'TODOS'
        bVal = b.digitos_nit || 'TODOS'
        break
      case 'tipo_tercero':
        aVal = a.tipo_tercero?.codigo || 'TODOS'
        bVal = b.tipo_tercero?.codigo || 'TODOS'
        break
      case 'tipo_regimen':
        aVal = a.tipo_regimen?.codigo || 'TODOS'
        bVal = b.tipo_regimen?.codigo || 'TODOS'
        break
      case 'fecha_limite':
        aVal = new Date(a.fecha_limite).getTime()
        bVal = new Date(b.fecha_limite).getTime()
        break
      case 'fecha_actualizacion':
        aVal = new Date(a.fecha_actualizacion || 0).getTime()
        bVal = new Date(b.fecha_actualizacion || 0).getTime()
        break
      default:
        return 0
    }
    
    if (aVal < bVal) return calendarioSortOrder.value === 'asc' ? -1 : 1
    if (aVal > bVal) return calendarioSortOrder.value === 'asc' ? 1 : -1
    return 0
  })
  
  return filtered
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

const formatFileSize = formatBytes // Alias para consistencia

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

const editEmpresaSQL = async (empresa: any) => {
  try {
    // Cargar datos completos de la empresa
    const response = await api.get(`/api/empresas-servidor/${empresa.id}/`)
    editingEmpresaSQL.value = response
    empresaSQLContent.value = response.consulta_sql || ''
    showEditEmpresaSQL.value = true
  } catch (error: any) {
    console.error('Error cargando empresa:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar empresa',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const saveEmpresaSQL = async () => {
  if (!editingEmpresaSQL.value) return
  
  try {
    await api.patch(`/api/empresas-servidor/${editingEmpresaSQL.value.id}/`, {
      consulta_sql: empresaSQLContent.value
    })
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Consulta SQL Guardada!',
      text: `Consulta SQL de ${editingEmpresaSQL.value.nombre} actualizada exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showEditEmpresaSQL.value = false
    editingEmpresaSQL.value = null
    empresaSQLContent.value = ''
    await loadEmpresas()
  } catch (error: any) {
    console.error('Error guardando consulta SQL:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al guardar consulta SQL',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const editEmpresaConfig = async (empresa: any) => {
  try {
    // Cargar datos completos de la empresa
    const response = await api.get(`/api/empresas-servidor/${empresa.id}/`)
    editingEmpresaConfig.value = response
    // Convertir configuracion a JSON string para edición
    empresaConfigContent.value = JSON.stringify(response.configuracion || {}, null, 2)
    showEditEmpresaConfig.value = true
  } catch (error: any) {
    console.error('Error cargando empresa:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar empresa',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const saveEmpresaConfig = async () => {
  if (!editingEmpresaConfig.value) return
  
  try {
    // Validar que sea JSON válido
    let configObj
    try {
      configObj = JSON.parse(empresaConfigContent.value)
    } catch (e) {
      const Swal = (await import('sweetalert2')).default
      await Swal.fire({
        title: 'Error de Formato',
        text: 'La configuración debe ser un JSON válido',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      return
    }
    
    await api.patch(`/api/empresas-servidor/${editingEmpresaConfig.value.id}/`, {
      configuracion: configObj
    })
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Configuración Guardada!',
      text: `Configuración de ${editingEmpresaConfig.value.nombre} actualizada exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showEditEmpresaConfig.value = false
    editingEmpresaConfig.value = null
    empresaConfigContent.value = ''
    await loadEmpresas()
  } catch (error: any) {
    console.error('Error guardando configuración:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al guardar configuración',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
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

const exportEmpresas = () => {
  try {
    const dataToExport = serverEmpresasList.value.map(e => ({
      'Código': e.codigo,
      'Nombre': e.nombre,
      'NIT': e.nit || e.nit_normalizado,
      'Representante Legal': e.representante_legal || '',
      'Año Fiscal': e.anio_fiscal,
      'Archivo': e.ruta_base ? e.ruta_base.split('/').pop() || e.ruta_base.split('\\').pop() : '',
      'Último Backup': e.ultimo_backup ? formatDate(e.ultimo_backup.fecha_backup) : 'Sin backup',
      'Tamaño Backup': e.ultimo_backup ? formatFileSize(e.ultimo_backup.tamano_bytes) : ''
    }))
    
    exportToCSV(dataToExport, `empresas_servidor_${selectedServerForEmpresas.value}_${new Date().toISOString().split('T')[0]}.csv`)
    
    const { success } = useToast()
    success('Empresas exportadas exitosamente')
  } catch (error: any) {
    console.error('Error exportando empresas:', error)
    const { error: showError } = useToast()
    showError('Error al exportar empresas')
  }
}

const viewServerEmpresas = async (serverId: number) => {
  selectedServerForEmpresas.value = serverId
  loadingServerEmpresas.value = true
  try {
    const empresasResponse = await api.get<any>(`/api/empresas-servidor/?servidor=${serverId}`)
    const empresasData = Array.isArray(empresasResponse) ? empresasResponse : (empresasResponse as any).results || []
    
    // Cargar último backup para cada empresa
    for (const empresa of empresasData) {
      try {
        const ultimoBackup = await api.get<any>(`/api/empresas-servidor/${empresa.id}/ultimo_backup/`)
        empresa.ultimo_backup = ultimoBackup || null
      } catch (error: any) {
        // 404 significa que no hay backups, lo cual es válido
        if (error?.status === 404 || error?.statusCode === 404) {
          empresa.ultimo_backup = null
        } else {
          console.warn(`Error obteniendo último backup para empresa ${empresa.id}:`, error)
          empresa.ultimo_backup = null
        }
      }
    }
    
    serverEmpresasList.value = empresasData
    empresasPagination.reset()
    showServerEmpresasModal.value = true
  } catch (error: any) {
    console.error('Error cargando empresas del servidor:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar empresas',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingServerEmpresas.value = false
  }
}

const editEmpresa = (empresa: any) => {
  editingEmpresa.value = { ...empresa }
  showEditEmpresaModal.value = true
}

const saveEmpresa = async () => {
  if (!editingEmpresa.value) return
  
  try {
    await api.patch(`/api/empresas-servidor/${editingEmpresa.value.id}/actualizar_campos/`, {
      nit: editingEmpresa.value.nit,
      nombre: editingEmpresa.value.nombre,
      anio_fiscal: editingEmpresa.value.anio_fiscal,
      representante_legal: editingEmpresa.value.representante_legal
    })
    
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Éxito',
      text: 'Empresa actualizada correctamente',
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    
    showEditEmpresaModal.value = false
    editingEmpresa.value = null
    
    // Recargar lista de empresas
    if (selectedServerForEmpresas.value) {
      await viewServerEmpresas(selectedServerForEmpresas.value)
    }
  } catch (error: any) {
    console.error('Error guardando empresa:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al guardar empresa',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const hacerBackupEmpresa = async (empresaId: number) => {
  if (!activeS3Config.value || !activeS3Config.value.id) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Configuración S3',
      text: 'Debes guardar una configuración S3 activa antes de crear backups.',
      icon: 'warning',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }

  try {
    const response = await api.post<any>('/api/backups-s3/realizar_backup/', {
      empresa_id: empresaId,
      configuracion_s3_id: activeS3Config.value.id
    })

    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Backup iniciado',
      text: `Se inició la tarea de backup. Task ID: ${response.task_id}`,
      icon: 'info',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } catch (error: any) {
    console.error('Error iniciando backup:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al iniciar el backup',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const toggleEmpresaMenu = (empresaId: number) => {
  empresaMenuOpen.value = empresaMenuOpen.value === empresaId ? null : empresaId
  backupMenuOpen.value = null
}

const handleBackupClick = (empresa: any) => {
  if (backupMenuOpen.value === empresa.id) {
    backupMenuOpen.value = null
  } else {
    backupMenuOpen.value = empresa.id
    empresaMenuOpen.value = null
  }
}

const downloadBackupFromEmpresa = async (backupId: number, formato: 'fbk' | 'gdb' = 'fbk') => {
  backupMenuOpen.value = null
  try {
    const backup = { id: backupId }
    if (formato === 'gdb') {
      // Solicitar GDB por email
      await requestGdbDownload(backupId, null)
    } else {
      // Descarga directa FBK
      await downloadBackup(backup)
    }
  } catch (error: any) {
    console.error('Error descargando backup:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al descargar backup',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const requestGdbDownload = async (backupId: number, empresa: any | null) => {
  backupMenuOpen.value = null
  const Swal = (await import('sweetalert2')).default
  
  const emailResult = await Swal.fire({
    title: 'Email para descarga GDB',
    text: 'Ingresa tu email para recibir el link de descarga seguro',
    input: 'email',
    inputPlaceholder: 'tu@email.com',
    inputValidator: (value) => {
      if (!value) {
        return 'Debes ingresar un email válido'
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        return 'Email inválido'
      }
      return null
    },
    showCancelButton: true,
    confirmButtonText: 'Enviar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (emailResult.isDismissed || !emailResult.value) return
  
  try {
    await api.post(`/api/backups-s3/${backupId}/solicitar_descarga_gdb/`, {
      email: emailResult.value
    })
    
    await Swal.fire({
      title: 'Solicitud recibida',
      html: `
        <p>Se está procesando la conversión a GDB.</p>
        <p>Recibirás un correo en <strong>${emailResult.value}</strong> con el link de descarga en breve.</p>
        <p><small>El link será válido por 24 horas.</small></p>
      `,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    
    // Recargar lista de empresas para actualizar último backup
    if (selectedServerForEmpresas.value) {
      await viewServerEmpresas(selectedServerForEmpresas.value)
    }
  } catch (error: any) {
    console.error('Error solicitando descarga GDB:', error)
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al solicitar la descarga',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const descargarUltimoBackupEmpresa = async (empresaId: number) => {
  try {
    // Obtener último backup
    const ultimoBackup = await api.get<any>(`/api/empresas-servidor/${empresaId}/ultimo_backup/`)
    
    if (!ultimoBackup) {
      const Swal = (await import('sweetalert2')).default
      await Swal.fire({
        title: 'Sin backups',
        text: 'Esta empresa no tiene backups disponibles.',
        icon: 'info',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      return
    }
    
    // Llamar a la función de descarga
    await downloadBackup(ultimoBackup)
  } catch (error: any) {
    console.error('Error obteniendo último backup:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al obtener último backup',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
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
// Cerrar menús al hacer clic fuera
onMounted(() => {
  document.addEventListener('click', (e) => {
    if (!(e.target as HTMLElement).closest('.dropdown-menu-container') && 
        !(e.target as HTMLElement).closest('.backup-info-clickable') &&
        !(e.target as HTMLElement).closest('.backup-menu')) {
      openServerMenu.value = null
      openUserMenu.value = null
      empresaMenuOpen.value = null
      backupMenuOpen.value = null
    }
  })
})

watch(userActiveTab, (newTab) => {
  if (activeSection.value === 'usuarios') {
    if (newTab === 'permisos') {
      if (users.value.length === 0) loadUsers()
      if (empresas.value.length === 0) loadEmpresas()
      loadPermisos()
    } else if (newTab === 'tenant-profiles') {
      if (users.value.length === 0) loadUsers()
      loadTenantProfiles()
    }
  }
})

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
  } else if (newSection === 'usuarios') {
    // Cargar usuarios automáticamente al cambiar a esta pestaña
    loadUsers()
  } else if (newSection === 'api-keys') {
    // Cargar API Keys y empresas automáticamente
    if (empresas.value.length === 0) {
      loadEmpresas()
    }
    loadApiKeys()
  } else if (newSection === 'dominios') {
    // Cargar dominios y empresas automáticamente
    if (empresas.value.length === 0) {
      loadEmpresas()
    }
    loadDominios()
  } else if (newSection === 'pasarelas') {
    // Cargar pasarelas automáticamente
    loadPasarelas()
  } else if (newSection === 'usuarios') {
    // Cargar usuarios, permisos y tenant profiles automáticamente
    if (users.value.length === 0) loadUsers()
    if (empresas.value.length === 0) loadEmpresas()
    if (userActiveTab.value === 'permisos') loadPermisos()
    if (userActiveTab.value === 'tenant-profiles') loadTenantProfiles()
  } else if (newSection === 'ruts') {
    // Cargar RUTs automáticamente
    loadRuts()
  } else if (newSection === 'calendario-tributario') {
    // Cargar calendario tributario automáticamente
    loadCalendarioTributario()
  } else if (newSection === 'backups-s3') {
    // Cargar configuración S3, empresas y backups al entrar en la sección
    if (empresas.value.length === 0) {
      loadEmpresas()
    }
    loadS3Config()
    reloadBackupsAndStats()
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
  servidor: null,
  dias_validez: 365
})

// Lista de NITs únicos para el selector
const uniqueNits = computed(() => {
  const nitsMap = new Map<string, string>()
  empresas.value.forEach(emp => {
    if (emp.nit && !nitsMap.has(emp.nit)) {
      // Usar el nombre de la primera empresa con ese NIT
      nitsMap.set(emp.nit, emp.nombre)
    }
  })
  return Array.from(nitsMap.entries()).map(([nit, nombre]) => ({ nit, nombre }))
})

// Auto-llenar nombre cuando se selecciona NIT
const onNitSelected = () => {
  if (newApiKey.value.nit) {
    const selected = uniqueNits.value.find(n => n.nit === newApiKey.value.nit)
    if (selected) {
      newApiKey.value.nombre_cliente = selected.nombre
    }
  }
}

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
    newApiKey.value = { nit: '', nombre_cliente: '', servidor: null, dias_validez: 365 }
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

const manageCalendarioNits = async (keyId: number) => {
  selectedApiKeyForCalendario.value = keyId
  showManageCalendarioNits.value = true
  selectedRutNits.value = []
  rutSearchResults.value = []
  rutSearchQuery.value = ''
  await loadCalendarioNits()
}

const loadCalendarioNits = async () => {
  if (!selectedApiKeyForCalendario.value) return
  
  loadingCalendarioNits.value = true
  try {
    const response = await api.get(`/api/api-keys/${selectedApiKeyForCalendario.value}/nits-calendario/`)
    calendarioNits.value = response.nits || []
  } catch (error: any) {
    console.error('Error cargando NITs de calendario:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar NITs de calendario',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingCalendarioNits.value = false
  }
}

const searchRuts = async () => {
  if (!rutSearchQuery.value.trim()) return
  
  searchingRuts.value = true
  try {
    const query = rutSearchQuery.value.trim()
    const response = await api.get('/api/ruts/', {
      params: {
        search: query,
        limit: 50
      }
    })
    
    // Si es un array, usar directamente; si es objeto con results, usar results
    const ruts = Array.isArray(response) ? response : (response.results || [])
    
    rutSearchResults.value = ruts.map((rut: any) => ({
      id: rut.id,
      nit: rut.nit,
      nit_normalizado: rut.nit_normalizado,
      razon_social: rut.razon_social,
      tipo_contribuyente: rut.tipo_contribuyente,
      dv: rut.dv
    }))
    
    // Filtrar NITs que ya están asociados
    const nitsAsociados = new Set(calendarioNits.value.map((n: any) => n.nit_normalizado))
    rutSearchResults.value = rutSearchResults.value.filter((rut: any) => !nitsAsociados.has(rut.nit_normalizado))
    
  } catch (error: any) {
    console.error('Error buscando RUTs:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al buscar RUTs',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    searchingRuts.value = false
  }
}

const asociarNitsCalendario = async () => {
  if (!selectedApiKeyForCalendario.value || selectedRutNits.value.length === 0) return
  
  loadingCalendarioNits.value = true
  try {
    await api.post(`/api/api-keys/${selectedApiKeyForCalendario.value}/nits-calendario/asociar/`, {
      nits: selectedRutNits.value
    })
    
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Éxito!',
      text: `${selectedRutNits.value.length} NIT(s) asociado(s) exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    
    selectedRutNits.value = []
    rutSearchResults.value = []
    rutSearchQuery.value = ''
    await loadCalendarioNits()
  } catch (error: any) {
    console.error('Error asociando NITs:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al asociar NITs',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingCalendarioNits.value = false
  }
}

const eliminarNitCalendario = async (nitId: number) => {
  if (!selectedApiKeyForCalendario.value) return
  
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar NIT?',
    text: '¿Estás seguro de que deseas eliminar este NIT del calendario tributario?',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    loadingCalendarioNits.value = true
    try {
      await api.delete(`/api/api-keys/${selectedApiKeyForCalendario.value}/nits-calendario/${nitId}/`)
      
      await Swal.fire({
        title: '¡Eliminado!',
        text: 'NIT eliminado exitosamente',
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      
      await loadCalendarioNits()
    } catch (error: any) {
      console.error('Error eliminando NIT:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar NIT',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    } finally {
      loadingCalendarioNits.value = false
    }
  }
}

// ========== USER MANAGEMENT FUNCTIONS ==========
const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const response = await api.get<any[]>('/api/usuarios/')
    users.value = Array.isArray(response) ? response : (response as any).results || []
    // Agregar formato de fecha
    users.value = users.value.map((u: any) => ({
      ...u,
      last_login_formatted: u.last_login_formatted || 'Nunca'
    }))
  } catch (error: any) {
    console.error('Error cargando usuarios:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar usuarios',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingUsers.value = false
  }
}

const createUser = async () => {
  if (!newUser.value.username || !newUser.value.password) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Usuario y contraseña son requeridos',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }
  
  try {
    await api.post('/api/usuarios/', newUser.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Usuario Creado!',
      text: `Usuario ${newUser.value.username} creado exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showCreateUser.value = false
    newUser.value = {
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      password: '',
      is_active: true,
      is_staff: false,
      is_superuser: false
    }
    await loadUsers()
  } catch (error: any) {
    console.error('Error creando usuario:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al crear usuario',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const editUser = (usr: any) => {
  editingUser.value = { ...usr }
  // No incluir password al editar
  delete editingUser.value.password
  showEditUser.value = true
}

const updateUser = async () => {
  if (!editingUser.value) return
  
  try {
    const updateData = { ...editingUser.value }
    // Si no hay password, no enviarlo
    if (!updateData.password) {
      delete updateData.password
    }
    
    await api.patch(`/api/usuarios/${editingUser.value.id}/`, updateData)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Usuario Actualizado!',
      text: `Usuario ${editingUser.value.username} actualizado exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showEditUser.value = false
    editingUser.value = null
    await loadUsers()
  } catch (error: any) {
    console.error('Error actualizando usuario:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al actualizar usuario',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const deleteUser = async (usr: any) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar Usuario?',
    text: `¿Estás seguro de eliminar el usuario "${usr.username}"? Esta acción no se puede deshacer.`,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.delete(`/api/usuarios/${usr.id}/`)
      await Swal.fire({
        title: '¡Usuario Eliminado!',
        text: `Usuario ${usr.username} eliminado exitosamente`,
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadUsers()
    } catch (error: any) {
      console.error('Error eliminando usuario:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar usuario',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

const toggleUserMenu = (userId: number) => {
  openUserMenu.value = openUserMenu.value === userId ? null : userId
}

const viewUserPermisos = (userId: number) => {
  userActiveTab.value = 'permisos'
  openUserMenu.value = null
  // Filtrar permisos por usuario si es necesario
  if (users.value.length === 0) loadUsers()
  if (empresas.value.length === 0) loadEmpresas()
  loadPermisos()
}

const viewUserTenantProfile = (userId: number) => {
  userActiveTab.value = 'tenant-profiles'
  openUserMenu.value = null
  if (users.value.length === 0) loadUsers()
  loadTenantProfiles()
}

const sortCalendario = (column: string) => {
  if (calendarioSortBy.value === column) {
    calendarioSortOrder.value = calendarioSortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    calendarioSortBy.value = column
    calendarioSortOrder.value = 'asc'
  }
}

const resetCalendarioFilters = () => {
  calendarioFilters.value = {
    impuesto: '',
    tipo_tercero: '',
    tipo_regimen: '',
    digitos_nit: ''
  }
  calendarioPagination.reset()
}

const exportCalendario = () => {
  try {
    const dataToExport = filteredAndSortedVigencias.value.map(v => ({
      'Impuesto Código': v.impuesto?.codigo || '',
      'Impuesto Nombre': v.impuesto?.nombre || '',
      'Dígitos NIT': v.digitos_nit || 'TODOS',
      'Tipo Tercero': v.tipo_tercero?.codigo || 'TODOS',
      'Tipo Régimen': v.tipo_regimen?.codigo || 'TODOS',
      'Fecha Límite': v.fecha_limite,
      'Descripción': v.descripcion || '',
      'Última Actualización': v.fecha_actualizacion || ''
    }))
    
    exportToCSV(dataToExport, `calendario_tributario_${new Date().toISOString().split('T')[0]}.csv`)
    
    const { success } = useToast()
    success('Calendario exportado exitosamente')
  } catch (error: any) {
    console.error('Error exportando calendario:', error)
    const { error: showError } = useToast()
    showError('Error al exportar calendario')
  }
}

const resetUserPassword = async (usr: any) => {
  const Swal = (await import('sweetalert2')).default
  const { value: newPassword } = await Swal.fire({
    title: `Resetear Contraseña de ${usr.username}`,
    input: 'text',
    inputLabel: 'Nueva Contraseña',
    inputPlaceholder: 'Ingresa la nueva contraseña',
    showCancelButton: true,
    confirmButtonText: 'Resetear',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' },
    inputValidator: (value) => {
      if (!value) {
        return 'Debes ingresar una contraseña'
      }
      if (value.length < 8) {
        return 'La contraseña debe tener al menos 8 caracteres'
      }
    }
  })
  
  if (newPassword) {
    try {
      await api.post(`/api/usuarios/${usr.id}/reset_password/`, {
        new_password: newPassword
      })
      await Swal.fire({
        title: '¡Contraseña Actualizada!',
        text: `La contraseña de ${usr.username} ha sido actualizada exitosamente`,
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    } catch (error: any) {
      console.error('Error reseteando contraseña:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al resetear contraseña',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

// ========== DOMINIOS FUNCTIONS ==========
const loadDominios = async () => {
  loadingDominios.value = true
  try {
    const response = await api.get<any[]>('/api/empresa-dominios/')
    dominios.value = Array.isArray(response) ? response : (response as any).results || []
  } catch (error: any) {
    console.error('Error cargando dominios:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar dominios',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingDominios.value = false
  }
}

const onDominioNitSelected = async () => {
  if (newDominio.value.nit) {
    // Buscar empresa con año fiscal más reciente para este NIT
    const empresasMismoNit = empresas.value
      .filter(e => e.nit === newDominio.value.nit)
      .sort((a, b) => b.anio_fiscal - a.anio_fiscal)
    
    if (empresasMismoNit.length > 0) {
      const empresaMasReciente = empresasMismoNit[0]
      // El backend se encargará de asignar empresa_servidor y anio_fiscal automáticamente
      // Solo mostramos información al usuario
      console.log(`Empresa más reciente encontrada: ${empresaMasReciente.nombre} (Año: ${empresaMasReciente.anio_fiscal})`)
    }
  }
}

const createDominio = async () => {
  if (!newDominio.value.dominio || !newDominio.value.nit) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Dominio y NIT son requeridos',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }
  
  try {
    await api.post('/api/empresa-dominios/', newDominio.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Dominio Creado!',
      text: `Dominio ${newDominio.value.dominio} creado exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showCreateDominio.value = false
    newDominio.value = {
      dominio: '',
      nit: '',
      servidor: null,
      modo: 'ecommerce',
      activo: true
    }
    await loadDominios()
  } catch (error: any) {
    console.error('Error creando dominio:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al crear dominio',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const editDominio = (dominio: any) => {
  editingDominio.value = { ...dominio }
  showEditDominio.value = true
}

const updateDominio = async () => {
  if (!editingDominio.value) return
  
  try {
    await api.patch(`/api/empresa-dominios/${editingDominio.value.id}/`, editingDominio.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Dominio Actualizado!',
      text: `Dominio ${editingDominio.value.dominio} actualizado exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showEditDominio.value = false
    editingDominio.value = null
    await loadDominios()
  } catch (error: any) {
    console.error('Error actualizando dominio:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al actualizar dominio',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const deleteDominio = async (dominio: any) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar Dominio?',
    text: `¿Estás seguro de eliminar el dominio "${dominio.dominio}"? Esta acción no se puede deshacer.`,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.delete(`/api/empresa-dominios/${dominio.id}/`)
      await Swal.fire({
        title: '¡Dominio Eliminado!',
        text: `Dominio ${dominio.dominio} eliminado exitosamente`,
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadDominios()
    } catch (error: any) {
      console.error('Error eliminando dominio:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar dominio',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

// ========== PASARELAS FUNCTIONS ==========
const loadPasarelas = async () => {
  loadingPasarelas.value = true
  try {
    const response = await api.get<any[]>('/api/pasarelas-pago/')
    pasarelas.value = Array.isArray(response) ? response : (response as any).results || []
  } catch (error: any) {
    console.error('Error cargando pasarelas:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar pasarelas',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingPasarelas.value = false
  }
}

const createPasarela = async () => {
  if (!newPasarela.value.codigo || !newPasarela.value.nombre) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Código y nombre son requeridos',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }
  
  try {
    // Validar y parsear configuración JSON
    let configObj = {}
    if (pasarelaConfigContent.value.trim()) {
      try {
        configObj = JSON.parse(pasarelaConfigContent.value)
      } catch (e) {
        const Swal = (await import('sweetalert2')).default
        await Swal.fire({
          title: 'Error de Formato',
          text: 'La configuración debe ser un JSON válido',
          icon: 'error',
          confirmButtonText: 'Aceptar',
          customClass: { container: 'swal-z-index-fix' }
        })
        return
      }
    }
    
    await api.post('/api/pasarelas-pago/', {
      ...newPasarela.value,
      configuracion: configObj
    })
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Pasarela Creada!',
      text: `Pasarela ${newPasarela.value.nombre} creada exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showCreatePasarela.value = false
    newPasarela.value = {
      codigo: '',
      nombre: '',
      activa: true,
      configuracion: {}
    }
    pasarelaConfigContent.value = '{}'
    await loadPasarelas()
  } catch (error: any) {
    console.error('Error creando pasarela:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al crear pasarela',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const editPasarela = (pasarela: any) => {
  editingPasarela.value = { ...pasarela }
  // Convertir configuración a JSON string para edición
  pasarelaConfigContent.value = JSON.stringify(pasarela.configuracion || {}, null, 2)
  showEditPasarela.value = true
}

const updatePasarela = async () => {
  if (!editingPasarela.value) return
  
  try {
    // Validar y parsear configuración JSON
    let configObj = {}
    if (pasarelaConfigContent.value.trim()) {
      try {
        configObj = JSON.parse(pasarelaConfigContent.value)
      } catch (e) {
        const Swal = (await import('sweetalert2')).default
        await Swal.fire({
          title: 'Error de Formato',
          text: 'La configuración debe ser un JSON válido',
          icon: 'error',
          confirmButtonText: 'Aceptar',
          customClass: { container: 'swal-z-index-fix' }
        })
        return
      }
    }
    
    await api.patch(`/api/pasarelas-pago/${editingPasarela.value.codigo}/`, {
      ...editingPasarela.value,
      configuracion: configObj
    })
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Pasarela Actualizada!',
      text: `Pasarela ${editingPasarela.value.nombre} actualizada exitosamente`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showEditPasarela.value = false
    editingPasarela.value = null
    pasarelaConfigContent.value = '{}'
    await loadPasarelas()
  } catch (error: any) {
    console.error('Error actualizando pasarela:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al actualizar pasarela',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const deletePasarela = async (pasarela: any) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar Pasarela?',
    text: `¿Estás seguro de eliminar la pasarela "${pasarela.nombre}"? Esta acción no se puede deshacer.`,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.delete(`/api/pasarelas-pago/${pasarela.codigo}/`)
      await Swal.fire({
        title: '¡Pasarela Eliminada!',
        text: `Pasarela ${pasarela.nombre} eliminada exitosamente`,
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadPasarelas()
    } catch (error: any) {
      console.error('Error eliminando pasarela:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar pasarela',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

const viewPasarelaConfig = async (pasarela: any) => {
  const Swal = (await import('sweetalert2')).default
  Swal.fire({
    title: `Configuración: ${pasarela.nombre}`,
    html: `
      <div style="text-align: left;">
        <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; max-height: 400px; text-align: left;">${JSON.stringify(pasarela.configuracion || {}, null, 2)}</pre>
      </div>
    `,
    icon: 'info',
    confirmButtonText: 'Cerrar',
    customClass: { container: 'swal-z-index-fix' }
  })
}

// ========== PERMISOS USUARIOS FUNCTIONS ==========
const loadPermisos = async () => {
  loadingPermisos.value = true
  try {
    const response = await api.get<any[]>('/api/permisos-usuarios/')
    permisosUsuarios.value = Array.isArray(response) ? response : (response as any).results || []
  } catch (error: any) {
    console.error('Error cargando permisos:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar permisos',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingPermisos.value = false
  }
}

const createPermiso = async () => {
  if (!newPermiso.value.usuario || !newPermiso.value.empresa_servidor) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Usuario y Empresa son requeridos',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }
  
  try {
    await api.post('/api/permisos-usuarios/', newPermiso.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Permiso Creado!',
      text: 'Permiso usuario-empresa creado exitosamente',
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showCreatePermiso.value = false
    newPermiso.value = {
      usuario: null,
      empresa_servidor: null,
      puede_ver: true,
      puede_editar: false,
      preferred_template: 'pro'
    }
    await loadPermisos()
  } catch (error: any) {
    console.error('Error creando permiso:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al crear permiso',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const editPermiso = (permiso: any) => {
  editingPermiso.value = { ...permiso }
  showEditPermiso.value = true
}

const updatePermiso = async () => {
  if (!editingPermiso.value) return
  
  try {
    await api.patch(`/api/permisos-usuarios/${editingPermiso.value.id}/`, editingPermiso.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Permiso Actualizado!',
      text: 'Permiso actualizado exitosamente',
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showEditPermiso.value = false
    editingPermiso.value = null
    await loadPermisos()
  } catch (error: any) {
    console.error('Error actualizando permiso:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al actualizar permiso',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const deletePermiso = async (permiso: any) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar Permiso?',
    text: `¿Estás seguro de eliminar el permiso de ${permiso.usuario_username} a ${permiso.empresa_nombre}?`,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.delete(`/api/permisos-usuarios/${permiso.id}/`)
      await Swal.fire({
        title: '¡Permiso Eliminado!',
        text: 'Permiso eliminado exitosamente',
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadPermisos()
    } catch (error: any) {
      console.error('Error eliminando permiso:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar permiso',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

// ========== TENANT PROFILES FUNCTIONS ==========
const loadTenantProfiles = async () => {
  loadingTenantProfiles.value = true
  try {
    const response = await api.get<any[]>('/api/tenant-profiles/')
    tenantProfiles.value = Array.isArray(response) ? response : (response as any).results || []
  } catch (error: any) {
    console.error('Error cargando tenant profiles:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar tenant profiles',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingTenantProfiles.value = false
  }
}

const createTenantProfile = async () => {
  if (!newTenantProfile.value.user || !newTenantProfile.value.subdomain) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Usuario y Subdomain son requeridos',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }
  
  try {
    await api.post('/api/tenant-profiles/', newTenantProfile.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Tenant Profile Creado!',
      text: 'Tenant profile creado exitosamente',
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showCreateTenantProfile.value = false
    newTenantProfile.value = {
      user: null,
      subdomain: '',
      preferred_template: 'pro'
    }
    await loadTenantProfiles()
  } catch (error: any) {
    console.error('Error creando tenant profile:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al crear tenant profile',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const editTenantProfile = (profile: any) => {
  editingTenantProfile.value = { ...profile }
  showEditTenantProfile.value = true
}

const updateTenantProfile = async () => {
  if (!editingTenantProfile.value) return
  
  try {
    await api.patch(`/api/tenant-profiles/${editingTenantProfile.value.id}/`, editingTenantProfile.value)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: '¡Tenant Profile Actualizado!',
      text: 'Tenant profile actualizado exitosamente',
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    showEditTenantProfile.value = false
    editingTenantProfile.value = null
    await loadTenantProfiles()
  } catch (error: any) {
    console.error('Error actualizando tenant profile:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al actualizar tenant profile',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const deleteTenantProfile = async (profile: any) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar Tenant Profile?',
    text: `¿Estás seguro de eliminar el tenant profile de ${profile.user_username}?`,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.delete(`/api/tenant-profiles/${profile.id}/`)
      await Swal.fire({
        title: '¡Tenant Profile Eliminado!',
        text: 'Tenant profile eliminado exitosamente',
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadTenantProfiles()
    } catch (error: any) {
      console.error('Error eliminando tenant profile:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar tenant profile',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

// ========== RUTS FUNCTIONS ==========
const loadRuts = async () => {
  loadingRuts.value = true
  try {
    const response = await api.get<any[]>('/api/ruts/')
    ruts.value = Array.isArray(response) ? response : (response as any).results || []
  } catch (error: any) {
    console.error('Error cargando RUTs:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar RUTs',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingRuts.value = false
  }
}

// =========================
// Backups S3
// =========================

const ensureActiveS3Config = () => {
  if (!activeS3Config.value) {
    activeS3Config.value = {
      id: null,
      nombre: 'Backups Principal',
      bucket_name: '',
      region: 'us-east-1',
      access_key_id: '',
      secret_access_key: '',
      endpoint_url: '',
      activo: true
    }
  }
}

const loadS3Config = async () => {
  loadingS3Config.value = true
  try {
    const response = await api.get<any[]>('/api/configuraciones-s3/')
    const data = Array.isArray(response) ? response : (response as any).results || []
    s3Configs.value = data
    if (data.length > 0) {
      // Por simplicidad usamos la primera configuración activa o la primera
      const activa = data.find((c: any) => c.activo) || data[0]
      activeS3Config.value = { ...activa, secret_access_key: '' }
    } else {
      ensureActiveS3Config()
    }
  } catch (error: any) {
    console.error('Error cargando configuración S3:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar configuración S3',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingS3Config.value = false
  }
}

const saveS3Config = async () => {
  ensureActiveS3Config()
  const config = activeS3Config.value
  if (!config.bucket_name || !config.access_key_id) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Faltan datos',
      text: 'Bucket y Access Key ID son obligatorios.',
      icon: 'warning',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }

  savingS3Config.value = true
  try {
    const payload = { ...config }
    // Si el usuario deja secret_access_key vacío en edición, no lo sobreescribimos
    if (!payload.secret_access_key) {
      delete payload.secret_access_key
    }

    let response: any
    if (config.id) {
      response = await api.put<any>(`/api/configuraciones-s3/${config.id}/`, payload)
    } else {
      response = await api.post<any>('/api/configuraciones-s3/', payload)
    }

    const saved = response as any
    activeS3Config.value = { ...saved, secret_access_key: '' }
    await loadS3Config()

    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Guardado',
      text: 'Configuración S3 guardada correctamente.',
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } catch (error: any) {
    console.error('Error guardando configuración S3:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al guardar configuración S3',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    savingS3Config.value = false
  }
}

const loadBackupsForSelectedEmpresa = async () => {
  if (!selectedBackupEmpresaId.value) {
    backupsS3.value = []
    backupStats.value = null
    return
  }
  loadingBackupsS3.value = true
  try {
    const empresaId = selectedBackupEmpresaId.value
    const response = await api.get<any[]>(`/api/backups-s3/?empresa_id=${empresaId}`)
    backupsS3.value = Array.isArray(response) ? response : (response as any).results || []
  } catch (error: any) {
    console.error('Error cargando backups S3:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar backups S3',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingBackupsS3.value = false
  }
}

const loadBackupStatsForSelectedEmpresa = async () => {
  if (!selectedBackupEmpresaId.value) {
    backupStats.value = null
    return
  }
  try {
    const empresaId = selectedBackupEmpresaId.value
    const response = await api.get<any>(`/api/backups-s3/estadisticas_empresa/?empresa_id=${empresaId}`)
    backupStats.value = response
  } catch (error: any) {
    console.error('Error cargando estadísticas de backups:', error)
    backupStats.value = null
  }
}

const reloadBackupsAndStats = async () => {
  if (!selectedBackupEmpresaId.value) return
  await Promise.all([
    loadBackupsForSelectedEmpresa(),
    loadBackupStatsForSelectedEmpresa()
  ])
}

const triggerBackupForSelectedEmpresa = async () => {
  if (!selectedBackupEmpresaId.value) return
  triggeringBackup.value = true
  try {
    if (!activeS3Config.value || !activeS3Config.value.id) {
      const Swal = (await import('sweetalert2')).default
      await Swal.fire({
        title: 'Configuración S3',
        text: 'Debes guardar una configuración S3 activa antes de crear backups.',
        icon: 'warning',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      return
    }

    const empresaId = selectedBackupEmpresaId.value
    const response = await api.post<any>('/api/backups-s3/realizar_backup/', {
      empresa_id: empresaId,
      configuracion_s3_id: activeS3Config.value.id
    })

    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Backup iniciado',
      text: `Se inició la tarea de backup. Task ID: ${response.task_id}`,
      icon: 'info',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })

    // No esperamos al resultado; solo recargamos la lista después de un pequeño delay
    setTimeout(() => {
      reloadBackupsAndStats()
    }, 5000)
  } catch (error: any) {
    console.error('Error iniciando backup S3:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al iniciar el backup',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    triggeringBackup.value = false
  }
}

const downloadBackup = async (backup: any) => {
  const Swal = (await import('sweetalert2')).default
  
  // Preguntar formato
  const result = await Swal.fire({
    title: 'Formato de descarga',
    text: '¿En qué formato deseas descargar el backup?',
    icon: 'question',
    showCancelButton: true,
    confirmButtonText: 'FBK (Backup)',
    cancelButtonText: 'GDB (Base de datos)',
    showDenyButton: true,
    denyButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })

  if (result.isDismissed || result.isDenied) return

  const formato = result.isConfirmed ? 'fbk' : 'gdb'
  
  // Si es GDB, pedir email
  if (formato === 'gdb') {
    const emailResult = await Swal.fire({
      title: 'Email para descarga GDB',
      text: 'Ingresa tu email para recibir el link de descarga seguro',
      input: 'email',
      inputPlaceholder: 'tu@email.com',
      inputValidator: (value) => {
        if (!value) {
          return 'Debes ingresar un email válido'
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
          return 'Email inválido'
        }
        return null
      },
      showCancelButton: true,
      confirmButtonText: 'Enviar',
      cancelButtonText: 'Cancelar',
      customClass: { container: 'swal-z-index-fix' }
    })
    
    if (emailResult.isDismissed || !emailResult.value) return
    
    downloadingBackupId.value = backup.id
    try {
      const config = useRuntimeConfig()
      const { accessToken, apiKey } = useAuthState()
      
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      
      if (accessToken.value) {
        headers['Authorization'] = `Bearer ${accessToken.value}`
      }
      
      if (apiKey.value) {
        headers['Api-Key'] = apiKey.value
      }
      
      // Solicitar conversión a GDB y envío por correo
      await api.post(`/api/backups-s3/${backup.id}/solicitar_descarga_gdb/`, {
        email: emailResult.value
      })
      
      await Swal.fire({
        title: 'Solicitud recibida',
        html: `
          <p>Se está procesando la conversión a GDB.</p>
          <p>Recibirás un correo en <strong>${emailResult.value}</strong> con el link de descarga en breve.</p>
          <p><small>El link será válido por 24 horas.</small></p>
        `,
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    } catch (error: any) {
      console.error('Error solicitando descarga GDB:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al solicitar la descarga',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    } finally {
      downloadingBackupId.value = null
    }
    return
  }
  
  // Si es FBK, descarga directa
  downloadingBackupId.value = backup.id
  try {
    // Usar $fetch directamente para manejar blob response
    const config = useRuntimeConfig()
    const { accessToken, apiKey } = useAuthState()
    
    const headers: Record<string, string> = {}
    
    if (accessToken.value) {
      headers['Authorization'] = `Bearer ${accessToken.value}`
    }
    
    if (apiKey.value) {
      headers['Api-Key'] = apiKey.value
    }
    
    // Construir URL completa sin parámetros adicionales
    const downloadUrl = `${config.public.djangoApiUrl}/api/backups-s3/${backup.id}/descargar_backup/?formato=fbk`
    
    // Usar $fetch.raw para obtener la respuesta completa con headers
    const response = await $fetch.raw(downloadUrl, {
      method: 'GET',
      headers
    })
    
    // Obtener el contenido de la respuesta
    const responseData = response._data
    
    // Obtener headers de forma segura (puede ser objeto plano o Headers object)
    const headersObj = response.headers || {}
    const getHeader = (name: string): string => {
      if (typeof headersObj.get === 'function') {
        return headersObj.get(name) || ''
      }
      // Si es objeto plano, buscar en diferentes formatos
      const lowerName = name.toLowerCase()
      return headersObj[lowerName] || headersObj[name] || ''
    }
    
    // Verificar status code primero
    if (response.status < 200 || response.status >= 300) {
      // Es un error, intentar leer como JSON o texto
      let errorData: any
      if (responseData instanceof Blob) {
        const text = await responseData.text()
        try {
          errorData = JSON.parse(text)
        } catch {
          errorData = { error: text || `Error ${response.status}` }
        }
      } else if (typeof responseData === 'string') {
        try {
          errorData = JSON.parse(responseData)
        } catch {
          errorData = { error: responseData || `Error ${response.status}` }
        }
      } else {
        errorData = responseData || { error: `Error ${response.status}` }
      }
      throw { response: { data: errorData, status: response.status } }
    }
    
    // Verificar si la respuesta es un error JSON
    const contentType = getHeader('content-type')
    
    if (contentType.includes('application/json')) {
      // Es un error JSON, leerlo como texto y parsearlo
      let errorData: any
      if (responseData instanceof Blob) {
        const text = await responseData.text()
        try {
          errorData = JSON.parse(text)
        } catch {
          errorData = { error: text }
        }
      } else if (typeof responseData === 'string') {
        try {
          errorData = JSON.parse(responseData)
        } catch {
          errorData = { error: responseData }
        }
      } else {
        errorData = responseData
      }
      throw { response: { data: errorData, status: response.status } }
    }
    
    // Obtener el blob de la respuesta
    let blob: Blob
    if (responseData instanceof Blob) {
      blob = responseData
    } else if (responseData instanceof ArrayBuffer) {
      blob = new Blob([responseData])
    } else {
      // Si no es blob, intentar convertirlo
      blob = new Blob([String(responseData)])
    }
    
    // Crear URL del blob y descargar
    const blobUrlDownload = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = blobUrlDownload
    
    // Obtener nombre del archivo desde headers o usar el nombre del backup
    const contentDisposition = getHeader('content-disposition')
    let filename = backup.nombre_archivo
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i)
      if (filenameMatch) {
        filename = filenameMatch[1]
      }
    }
    
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(blobUrlDownload)
    
    await Swal.fire({
      title: 'Descarga iniciada',
      text: `El archivo ${filename} se está descargando.`,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } catch (error: any) {
    console.error('Error descargando backup:', error)
    
    // Intentar extraer el mensaje de error del response
    let errorMessage = 'Error al descargar backup'
    
    if (error?.response?.data) {
      // Si es un blob con error JSON, intentar leerlo
      if (error.response.data instanceof Blob) {
        try {
          const text = await error.response.data.text()
          const errorData = JSON.parse(text)
          errorMessage = errorData.error || errorData.message || text
        } catch {
          errorMessage = 'Error al descargar backup (formato de respuesta inválido)'
        }
      } else if (typeof error.response.data === 'object') {
        // Si es un objeto JSON normal
        errorMessage = error.response.data.error || error.response.data.message || JSON.stringify(error.response.data)
      } else {
        errorMessage = error.response.data
      }
    } else if (error?.data?.error) {
      errorMessage = error.data.error
    } else if (error?.message) {
      errorMessage = error.message
    }
    
    await Swal.fire({
      title: 'Error',
      text: errorMessage,
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    downloadingBackupId.value = null
  }
}

const deleteBackup = async (backup: any) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar backup?',
    text: `Se eliminará el backup ${backup.nombre_archivo} de S3. Esta acción no se puede deshacer.`,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })

  if (!result.isConfirmed) return

  deletingBackupId.value = backup.id
  try {
    await api.delete(`/api/backups-s3/${backup.id}/eliminar_backup/`)
    await reloadBackupsAndStats()
  } catch (error: any) {
    console.error('Error eliminando backup S3:', error)
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al eliminar backup',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    deletingBackupId.value = null
  }
}

const uploadRUTPDF = async () => {
  if (!selectedRUTFile.value && !selectedRUTZipFile.value) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Debes seleccionar un archivo PDF o un archivo ZIP',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }
  
  uploadingRUT.value = true
  try {
    const formData = new FormData()
    
    // Si es ZIP
    if (selectedRUTZipFile.value) {
      formData.append('archivo_zip', selectedRUTZipFile.value)
    } else {
      // Si es PDF individual
      formData.append('archivo_pdf', selectedRUTFile.value!)
      if (rutNitManual.value.trim()) {
        formData.append('nit', rutNitManual.value.trim())
      }
    }
    
    const response = await api.post('/api/ruts/subir-pdf/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }) as any
    
    const Swal = (await import('sweetalert2')).default
    
    // Verificar que response exista
    if (!response) {
      await Swal.fire({
        title: 'Error',
        text: 'No se recibió respuesta del servidor',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      return
    }
    
    // Si es procesamiento asíncrono (ZIP grande con Celery)
    if (response.procesamiento_asincrono && response.task_id) {
      // Monitorear progreso en tiempo real
      await monitorearProcesamientoRUTs(response.task_id, response.total || 0)
      return
    }
    
    // Si es ZIP, mostrar resultados masivos (solo si tiene reporte_txt)
    if (selectedRUTZipFile.value && response.reporte_txt) {
      rutReporteTxt.value = response.reporte_txt
      
      const fallidosHtml = response.detalles_fallidos && response.detalles_fallidos.length > 0
        ? `<div style="margin-top: 15px; max-height: 300px; overflow-y: auto; text-align: left;">
            <strong style="color: #d32f2f;">RUTs Fallidos (${response.detalles_fallidos.length}):</strong>
            <ul style="margin-top: 10px;">
              ${response.detalles_fallidos.map((f: any) => 
                `<li><strong>${f.archivo}</strong>: ${f.razon}</li>`
              ).join('')}
            </ul>
          </div>`
        : ''
      
      await Swal.fire({
        title: '¡ZIP Procesado!',
        html: `
          <div style="text-align: left;">
            <p><strong>Total procesados:</strong> ${response.total}</p>
            <p style="color: #4CAF50;"><strong>Exitosos:</strong> ${response.exitosos}</p>
            ${response.fallidos > 0 ? `<p style="color: #d32f2f;"><strong>Fallidos:</strong> ${response.fallidos}</p>` : ''}
            ${fallidosHtml}
            <div style="margin-top: 20px; padding: 10px; background: #f5f5f5; border-radius: 5px;">
              <strong>📄 Reporte TXT generado</strong><br>
              <button id="download-reporte" style="margin-top: 10px; padding: 8px 16px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Descargar Reporte TXT
              </button>
            </div>
          </div>
        `,
        icon: response.fallidos > 0 ? 'warning' : 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' },
        width: '700px',
        didOpen: () => {
          const btn = document.getElementById('download-reporte')
          if (btn) {
            btn.onclick = () => {
              const blob = new Blob([rutReporteTxt.value!], { type: 'text/plain' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `reporte_ruts_${new Date().toISOString().split('T')[0]}.txt`
              a.click()
              URL.revokeObjectURL(url)
            }
          }
        }
      })
    } else if (selectedRUTZipFile.value) {
      // ZIP procesado pero sin reporte_txt (caso raro)
      await Swal.fire({
        title: 'ZIP Procesado',
        text: response?.mensaje || 'El ZIP fue procesado, pero no se generó reporte.',
        icon: 'warning',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    } else {
      // PDF individual
      if (response && response.rut) {
        await Swal.fire({
          title: '¡RUT Procesado!',
          html: `
            <div style="text-align: left;">
              <p><strong>NIT:</strong> ${response.rut.nit || 'N/A'}-${response.rut.dv || ''}</p>
              <p><strong>Razón Social:</strong> ${response.rut.razon_social || 'N/A'}</p>
              <p><strong>Empresas asociadas encontradas:</strong> ${response.empresas_encontradas || 0}</p>
              <p style="margin-top: 10px; color: #4CAF50;">${response.mensaje || 'RUT procesado exitosamente'}</p>
            </div>
          `,
          icon: 'success',
          confirmButtonText: 'Aceptar',
          customClass: { container: 'swal-z-index-fix' }
        })
      } else {
        await Swal.fire({
          title: '¡RUT Procesado!',
          text: response?.mensaje || 'RUT procesado exitosamente',
          icon: 'success',
          confirmButtonText: 'Aceptar',
          customClass: { container: 'swal-z-index-fix' }
        })
      }
    }
    
    showUploadRUT.value = false
    selectedRUTFile.value = null
    selectedRUTZipFile.value = null
    rutNitManual.value = ''
    rutReporteTxt.value = null
    await loadRuts()
  } catch (error: any) {
    console.error('Error subiendo RUT:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al procesar el archivo',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    uploadingRUT.value = false
  }
}

const monitorearProcesamientoRUTs = async (taskId: string, totalArchivos: number) => {
  const Swal = (await import('sweetalert2')).default
  
  let intervalId: ReturnType<typeof setInterval> | null = null
  let isClosed = false
  
  // Función para actualizar la modal
  const actualizarModal = async (estado: any) => {
    if (isClosed) return
    
    const meta = estado.meta || {}
    const procesados = meta.procesados || 0
    const exitosos = meta.exitosos || 0
    const fallidos = meta.fallidos || 0
    const total = meta.total || totalArchivos
    const status = meta.status || estado.state || 'PROCESSING'
    const porcentaje = total > 0 ? Math.round((procesados / total) * 100) : 0
    
    const html = `
      <div style="text-align: left;">
        <div style="margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span><strong>Progreso:</strong></span>
            <span><strong>${procesados}/${total} (${porcentaje}%)</strong></span>
          </div>
          <div style="background: #e5e7eb; border-radius: 10px; height: 24px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%); height: 100%; width: ${porcentaje}%; transition: width 0.3s ease; display: flex; align-items: center; justify-content: center; color: white; font-size: 0.75rem; font-weight: 600;">
              ${porcentaje}%
            </div>
          </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 20px;">
          <div style="background: #f0f9ff; padding: 12px; border-radius: 8px; border-left: 4px solid #3b82f6;">
            <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 4px;">Total</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #1f2937;">${total}</div>
          </div>
          <div style="background: #f0fdf4; padding: 12px; border-radius: 8px; border-left: 4px solid #10b981;">
            <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 4px;">Exitosos</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">${exitosos}</div>
          </div>
          <div style="background: #fef2f2; padding: 12px; border-radius: 8px; border-left: 4px solid #ef4444;">
            <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 4px;">Fallidos</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #ef4444;">${fallidos}</div>
          </div>
        </div>
        
        <div style="background: #f9fafb; padding: 12px; border-radius: 8px; margin-top: 15px;">
          <div style="font-size: 0.85rem; color: #6b7280; margin-bottom: 4px;">Estado actual:</div>
          <div style="font-weight: 600; color: #1f2937;">
            ${status}
            ${meta.status && meta.status.includes(':') ? `<br><span style="font-size: 0.8em; color: #6b7280; font-weight: normal;">${meta.status.split(':').slice(1).join(':').trim()}</span>` : ''}
          </div>
        </div>
        
        <div style="margin-top: 15px; padding: 10px; background: #fef3c7; border-radius: 6px; font-size: 0.85rem; color: #92400e;">
          ⏳ Procesando... Por favor no cierres esta ventana.
        </div>
      </div>
    `
    
    Swal.update({
      html,
      showConfirmButton: false,
      allowOutsideClick: false,
      allowEscapeKey: false
    })
  }
  
  // Mostrar modal inicial
  Swal.fire({
    title: 'Procesando ZIP de RUTs',
    html: `
      <div style="text-align: left;">
        <p>Iniciando procesamiento...</p>
        <div style="margin-top: 15px;">
          <div style="background: #e5e7eb; border-radius: 10px; height: 24px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
          </div>
        </div>
      </div>
    `,
    icon: 'info',
    showConfirmButton: false,
    allowOutsideClick: false,
    allowEscapeKey: false,
    customClass: { container: 'swal-z-index-fix' },
    width: '700px',
    didOpen: () => {
      // Iniciar polling
      const pollStatus = async () => {
        try {
          const statusResponse = await api.get(`/api/celery/task-status/${taskId}/`)
          const estado = statusResponse as any
          
          if (estado.ready) {
            // Tarea completada
            if (intervalId) clearInterval(intervalId)
            
            if (estado.successful && estado.result) {
              const resultado = estado.result
              
              // Mostrar resultados finales
              const fallidosHtml = resultado.detalles_fallidos && resultado.detalles_fallidos.length > 0
                ? `<div style="margin-top: 15px; max-height: 300px; overflow-y: auto; text-align: left;">
                    <strong style="color: #d32f2f;">RUTs Fallidos (${resultado.detalles_fallidos.length}):</strong>
                    <ul style="margin-top: 10px;">
                      ${resultado.detalles_fallidos.map((f: any) => 
                        `<li><strong>${f.archivo}</strong>: ${f.razon}</li>`
                      ).join('')}
                    </ul>
                  </div>`
                : ''
              
              if (resultado.reporte_txt) {
                rutReporteTxt.value = resultado.reporte_txt
              }
              
              await Swal.fire({
                title: resultado.status === 'SUCCESS' ? '¡ZIP Procesado!' : 'Procesamiento Completado',
                html: `
                  <div style="text-align: left;">
                    <p><strong>Total procesados:</strong> ${resultado.total || 0}</p>
                    <p style="color: #4CAF50;"><strong>Exitosos:</strong> ${resultado.exitosos || 0}</p>
                    ${resultado.fallidos > 0 ? `<p style="color: #d32f2f;"><strong>Fallidos:</strong> ${resultado.fallidos}</p>` : ''}
                    ${fallidosHtml}
                    ${resultado.reporte_txt ? `
                      <div style="margin-top: 20px; padding: 10px; background: #f5f5f5; border-radius: 5px;">
                        <strong>📄 Reporte TXT generado</strong><br>
                        <button id="download-reporte" style="margin-top: 10px; padding: 8px 16px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;">
                          Descargar Reporte TXT
                        </button>
                      </div>
                    ` : ''}
                  </div>
                `,
                icon: resultado.fallidos > 0 ? 'warning' : 'success',
                confirmButtonText: 'Aceptar',
                customClass: { container: 'swal-z-index-fix' },
                width: '700px',
                didOpen: () => {
                  const btn = document.getElementById('download-reporte')
                  if (btn && rutReporteTxt.value) {
                    btn.onclick = () => {
                      const blob = new Blob([rutReporteTxt.value!], { type: 'text/plain' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `reporte_ruts_${new Date().toISOString().split('T')[0]}.txt`
                      a.click()
                      URL.revokeObjectURL(url)
                    }
                  }
                }
              })
            } else {
              // Error en la tarea
              await Swal.fire({
                title: 'Error en el Procesamiento',
                text: estado.error || 'Ocurrió un error al procesar el ZIP',
                icon: 'error',
                confirmButtonText: 'Aceptar',
                customClass: { container: 'swal-z-index-fix' }
              })
            }
            
            // Limpiar formulario
            showUploadRUT.value = false
            selectedRUTFile.value = null
            selectedRUTZipFile.value = null
            rutNitManual.value = ''
            rutReporteTxt.value = null
            await loadRuts()
            isClosed = true
          } else {
            // Actualizar progreso
            await actualizarModal(estado)
          }
        } catch (error: any) {
          console.error('Error consultando estado de tarea:', error)
          // Continuar intentando
        }
      }
      
      // Polling cada 2 segundos
      pollStatus() // Primera consulta inmediata
      intervalId = setInterval(pollStatus, 2000)
    },
    willClose: () => {
      isClosed = true
      if (intervalId) {
        clearInterval(intervalId)
        intervalId = null
      }
    }
  })
}

const onRUTZipSelected = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedRUTZipFile.value = target.files[0]
    selectedRUTFile.value = null // Limpiar PDF si hay ZIP
  }
}

const viewRUTDetails = async (rut: any) => {
  try {
    // Cargar empresas asociadas
    const response = await api.get(`/api/ruts/${rut.nit_normalizado}/empresas/`)
    selectedRUT.value = response.rut
    showRUTDetails.value = true
  } catch (error: any) {
    console.error('Error cargando detalles del RUT:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar detalles del RUT',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  }
}

const editRUT = (rut: any) => {
  // Por ahora solo mostrar detalles, la edición completa se puede agregar después
  viewRUTDetails(rut)
}

const deleteRUT = async (rut: any) => {
  const Swal = (await import('sweetalert2')).default
  const result = await Swal.fire({
    title: '¿Eliminar RUT?',
    html: `
      <div style="text-align: left;">
        <p>¿Estás seguro de eliminar el RUT de:</p>
        <p><strong>${rut.razon_social}</strong></p>
        <p>NIT: ${rut.nit}-${rut.dv}</p>
        <p style="color: #d32f2f; margin-top: 10px;">Esta acción no se puede deshacer.</p>
      </div>
    `,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    customClass: { container: 'swal-z-index-fix' }
  })
  
  if (result.isConfirmed) {
    try {
      await api.delete(`/api/ruts/${rut.nit_normalizado}/`)
      await Swal.fire({
        title: '¡RUT Eliminado!',
        text: 'RUT eliminado exitosamente',
        icon: 'success',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
      await loadRuts()
    } catch (error: any) {
      console.error('Error eliminando RUT:', error)
      await Swal.fire({
        title: 'Error',
        text: error?.data?.error || error?.message || 'Error al eliminar RUT',
        icon: 'error',
        confirmButtonText: 'Aceptar',
        customClass: { container: 'swal-z-index-fix' }
      })
    }
  }
}

const onRUTFileSelected = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedRUTFile.value = target.files[0]
  }
}

// Calendario Tributario
const loadCalendarioTributario = async () => {
  loadingCalendario.value = true
  try {
    const response = await api.get<any[]>('/api/calendario-tributario/')
    vigenciasTributarias.value = Array.isArray(response) ? response : (response as any).results || []
  } catch (error: any) {
    console.error('Error cargando calendario tributario:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al cargar calendario tributario',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    loadingCalendario.value = false
  }
}

const onCalendarioFileSelected = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedCalendarioFile.value = target.files[0]
  }
}

const uploadCalendarioExcel = async () => {
  if (!selectedCalendarioFile.value) {
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: 'Debes seleccionar un archivo Excel',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
    return
  }
  
  uploadingCalendario.value = true
  try {
    const formData = new FormData()
    formData.append('archivo_excel', selectedCalendarioFile.value)
    
    const response = await api.post('/api/calendario-tributario/subir-excel/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    const Swal = (await import('sweetalert2')).default
    const empresasInfo = response.data.empresas_asociadas || []
    const empresasHtml = empresasInfo.length > 0 
      ? `<div style="text-align: left; margin-top: 15px;">
          <strong>Empresas asociadas (${empresasInfo.length}):</strong>
          <ul style="margin-top: 10px; max-height: 200px; overflow-y: auto;">
            ${empresasInfo.map((e: any) => `<li>${e.nombre} (NIT: ${e.nit})</li>`).join('')}
          </ul>
        </div>`
      : ''
    
    await Swal.fire({
      title: '¡Calendario Procesado!',
      html: `
        <div style="text-align: left;">
          <p><strong>Total procesadas:</strong> ${response.data.total_procesadas || 0}</p>
          <p><strong>Creadas:</strong> ${response.data.creados || 0}</p>
          <p><strong>Actualizadas:</strong> ${response.data.actualizados || 0}</p>
          ${response.data.total_errores > 0 ? `<p style="color: #d32f2f;"><strong>Errores:</strong> ${response.data.total_errores}</p>` : ''}
          ${empresasHtml}
        </div>
      `,
      icon: 'success',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' },
      width: '600px'
    })
    
    showUploadCalendario.value = false
    selectedCalendarioFile.value = null
    await loadCalendarioTributario()
  } catch (error: any) {
    console.error('Error subiendo calendario:', error)
    const Swal = (await import('sweetalert2')).default
    await Swal.fire({
      title: 'Error',
      text: error?.data?.error || error?.message || 'Error al procesar el Excel del calendario',
      icon: 'error',
      confirmButtonText: 'Aceptar',
      customClass: { container: 'swal-z-index-fix' }
    })
  } finally {
    uploadingCalendario.value = false
  }
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

.modal-subtitle {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0.25rem 0 0 0;
  font-weight: 500;
}

.empresas-modal {
  max-width: 1400px !important;
}

.empresas-modal .modal-body {
  padding: 1.5rem;
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

/* Estilos mejorados para configuración S3 */
.two-column-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-top: 1.5rem;
}

@media (max-width: 1200px) {
  .two-column-layout {
    grid-template-columns: 1fr;
  }
}

.card {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card h3 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
}

.small-muted {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

.s3-config-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}

.label-text {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.375rem;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  transition: all 0.2s;
  background: #ffffff;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input::placeholder {
  color: #9ca3af;
}

.form-hint {
  display: block;
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

.checkbox-group {
  margin-top: 0.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  user-select: none;
}

.checkbox-input {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #3b82f6;
}

.checkbox-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

/* Estilos para Dropdown Menu */
.dropdown-menu-container {
  position: relative;
  display: inline-block;
}

.dropdown-trigger {
  position: relative;
}

.dropdown-trigger.active {
  background: #374151;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.25rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  min-width: 180px;
  z-index: 1000;
  overflow: hidden;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.625rem 1rem;
  border: none;
  background: none;
  text-align: left;
  font-size: 0.875rem;
  color: #374151;
  cursor: pointer;
  transition: background 0.15s;
}

.dropdown-item:hover:not(:disabled) {
  background: #f3f4f6;
}

.dropdown-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dropdown-item-danger {
  color: #dc2626;
}

.dropdown-item-danger:hover:not(:disabled) {
  background: #fee2e2;
  color: #991b1b;
}

.dropdown-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 0.25rem 0;
}

/* Estilos para Tabs */
.tabs-container {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #e5e7eb;
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  background: none;
  color: #6b7280;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #374151;
  background: #f9fafb;
}

.tab-btn.active {
  color: #1f2937;
  border-bottom-color: #1f2937;
  font-weight: 600;
}

/* Estilos para Filtros */
.filters-container {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.filter-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.filter-input {
  padding: 0.5rem 0.75rem;
  border: 1.5px solid #d1d5db;
  border-radius: 0.5rem;
  background: white;
  color: #1f2937;
  font-size: 0.875rem;
  min-width: 150px;
  transition: all 0.2s;
}

.filter-input:focus {
  outline: none;
  border-color: #4b5563;
  box-shadow: 0 0 0 3px rgba(75, 85, 99, 0.1);
}

/* Estilos para Ordenamiento en Tablas */
.sortable {
  cursor: pointer;
  user-select: none;
  position: relative;
  padding-right: 1.5rem;
}

.sortable:hover {
  background: #f9fafb;
}

.sort-icon {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  color: #9ca3af;
}

.sortable.sort-asc .sort-icon,
.sortable.sort-desc .sort-icon {
  color: #1f2937;
  font-weight: bold;
}

/* Estilos para columna de Último Backup */
.ultimo-backup-cell {
  position: relative;
}

.backup-info-clickable {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.5rem;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.backup-info-clickable:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.backup-date {
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 500;
}

.backup-size {
  font-size: 0.7rem;
  color: #9ca3af;
}

.backup-status {
  display: inline-block;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  text-align: center;
  line-height: 18px;
  font-size: 0.7rem;
}

.backup-status.status-completado {
  background: #d1fae5;
  color: #10b981;
}

.backup-status.status-error {
  background: #fee2e2;
  color: #dc2626;
}

.backup-status.status-pendiente,
.backup-status.status-procesando {
  background: #fef3c7;
  color: #f59e0b;
}

.backup-menu {
  min-width: 200px;
  z-index: 1001;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
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
