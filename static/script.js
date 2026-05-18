// Mock data for platforms and accounts
let platformAccounts = {
  meta_acc: [],
  yt_acc: [],
  x_acc: [],
  tiktok_acc: [],
  linkedin_acc: [],
  thread_acc: [],
}

const platformCompatibility = {
  meta_acc: {
    name: "Meta (Facebook/Instagram)",
    icon: "fab fa-facebook",
    color: "#1877f2",
    endpoint: "/meta/api/post/",
    requirements: {
      text: { facebook: true, instagram: false }, // Instagram requires media
      image: { facebook: true, instagram: true },
      video: { facebook: true, instagram: true },
      carousel: { facebook: true, instagram: true },
      maxFiles: 10,
      videoMaxSize: "4GB",
      imageFormats: ["jpg", "jpeg", "png", "gif"],
      videoFormats: ["mp4", "mov", "avi"],
    },
  },
  yt_acc: {
    name: "YouTube",
    icon: "fab fa-youtube",
    color: "#ff0000",
    endpoint: "/youtube/api/upload/",
    requirements: {
      text: false,
      image: false,
      video: true,
      carousel: false,
      maxFiles: 1,
      videoMaxSize: "256GB",
      videoFormats: ["mp4", "mov", "avi", "wmv", "flv", "webm"],
    },
  },
  x_acc: {
    name: "X (Twitter)",
    icon: "fab fa-x-twitter",
    color: "#000000",
    endpoint: "/x/api/post-to-x/",
    requirements: {
      text: true,
      image: true,
      video: true,
      carousel: false,
      maxFiles: 4,
      videoMaxSize: "512MB",
      imageFormats: ["jpg", "jpeg", "png", "gif"],
      videoFormats: ["mp4", "mov"],
    },
  },
  tiktok_acc: {
    name: "TikTok",
    icon: "fab fa-tiktok",
    color: "#000000",
    endpoint: "/tiktok/api/upload/",
    requirements: {
      text: false,
      image: false,
      video: true,
      carousel: false,
      maxFiles: 1,
      videoMaxSize: "287MB",
      videoFormats: ["mp4", "mov", "avi"],
    },
  },
  linkedin_acc: {
    name: "LinkedIn",
    icon: "fab fa-linkedin",
    color: "#0077b5",
    endpoint: "/linkedin/api/post/",
    requirements: {
      text: true,
      image: true,
      video: true,
      carousel: false,
      maxFiles: 1,
      videoMaxSize: "5GB",
      imageFormats: ["jpg", "jpeg", "png", "gif"],
      videoFormats: ["mp4", "mov", "avi", "wmv", "asf"],
    },
  },
  thread_acc: {
    name: "Threads",
    icon: "fab fa-threads",
    color: "#000000",
    endpoint: "/threads/api/post-to-threads/",
    requirements: {
      text: true,
      image: true,
      video: false,
      carousel: true,
      maxFiles: 10,
      imageFormats: ["jpg", "jpeg", "png", "gif"],
    },
  },
}

class ComposerApp {
  constructor() {
    this.selectedPlatforms = new Set()
    this.selectedAccounts = new Map()
    this.uploadedFiles = []
    this.tags = []

    this.initializeElements()
    this.bindEvents()
    this.loadAccountsFromBackend()
    this.renderPlatforms()
  }

  loadAccountsFromBackend() {
    // This will be populated by Django template context
    console.log("[debug] === LOADING ACCOUNTS FROM BACKEND ===")
    console.log("[debug] window.accountsData exists:", typeof window.accountsData !== "undefined")

    if (typeof window.accountsData !== "undefined") {
      console.log("[debug] Raw accountsData:", window.accountsData)

      // Log each platform's accounts in detail
      Object.entries(window.accountsData).forEach(([platformKey, accounts]) => {
        console.log(`[debug] Platform ${platformKey}:`, accounts.length, "accounts")
        accounts.forEach((account, index) => {
          console.log(`[debug] ${platformKey}[${index}]:`, {
            id: account.id,
            account_id: account.account_id,
            channel_id: account.channel_id,
            x_id: account.x_id,
            linkedin_id: account.linkedin_id,
            tiktok_id: account.tiktok_id,
            name: account.name,
            account_name: account.account_name,
            display_name: account.display_name,
            channel_title: account.channel_title,
            username: account.username,
            allProperties: Object.keys(account),
          })
        })
      })

      platformAccounts = window.accountsData
      console.log("[debug] platformAccounts updated:", platformAccounts)
    } else {
      console.log("[debug] ERROR: window.accountsData is not defined!")
    }
    console.log("[debug] === END LOADING ACCOUNTS ===")
  }

  initializeElements() {
    // Form elements
    this.postTitle = document.getElementById("postTitle")
    this.postDescription = document.getElementById("postDescription")
    this.tagInput = document.getElementById("tagInput")
    this.tagsContainer = document.getElementById("tagsContainer")
    this.fileInput = document.getElementById("fileInput")
    this.filePreview = document.getElementById("filePreview")
    this.uploadArea = document.getElementById("uploadArea")
    this.charCounter = document.getElementById("charCounter")
    this.publishBtn = document.getElementById("publishBtn")
    this.platformsGrid = document.getElementById("platformsGrid")

    // Modal elements
    this.accountSelectionModal = document.getElementById("accountSelectionModal")
    this.postingProgressModal = document.getElementById("postingProgressModal")
    this.closeModal = document.getElementById("closeModal")
    this.cancelPost = document.getElementById("cancelPost")
    this.confirmPost = document.getElementById("confirmPost")
    this.closeProgressModal = document.getElementById("closeProgressModal")
    this.platformsList = document.getElementById("platformsList")
    this.progressList = document.getElementById("progressList")
  }

  bindEvents() {
    // Character counter
    this.postDescription.addEventListener("input", () => {
      this.updateCharCounter()
      this.renderPlatforms() // Re-render to update compatibility
    })

    // Title input
    this.postTitle.addEventListener("input", () => {
      this.renderPlatforms() // Re-render to update compatibility
    })

    // Tag input
    this.tagInput.addEventListener("keydown", (e) => this.handleTagInput(e))

    // File upload
    this.fileInput.addEventListener("change", (e) => {
      this.handleFileUpload(e)
      this.renderPlatforms() // Re-render to update compatibility
    })
    this.uploadArea.addEventListener("dragover", (e) => this.handleDragOver(e))
    this.uploadArea.addEventListener("drop", (e) => {
      this.handleFileDrop(e)
      this.renderPlatforms() // Re-render to update compatibility
    })

    // Publish button
    this.publishBtn.addEventListener("click", () => this.showAccountSelection())

    // Modal events
    this.closeModal.addEventListener("click", () => this.hideAccountSelection())
    this.cancelPost.addEventListener("click", () => this.hideAccountSelection())
    this.confirmPost.addEventListener("click", () => this.startPosting())
    this.closeProgressModal.addEventListener("click", () => this.hidePostingProgress())

    // Close modals on overlay click
    this.accountSelectionModal.addEventListener("click", (e) => {
      if (e.target === this.accountSelectionModal) {
        this.hideAccountSelection()
      }
    })

    this.postingProgressModal.addEventListener("click", (e) => {
      if (e.target === this.postingProgressModal) {
        // Don't close progress modal on overlay click
      }
    })
  }

  renderPlatforms() {
    this.platformsGrid.innerHTML = ""

    Object.entries(platformCompatibility).forEach(([key, platform]) => {
      const accounts = platformAccounts[key] || []
      if (accounts.length === 0) return

      const isCompatible = this.checkPlatformCompatibility(key)
      const platformCard = document.createElement("div")
      platformCard.className = `platform-card ${!isCompatible ? "disabled" : ""}`
      platformCard.dataset.platform = key

      platformCard.innerHTML = `
        <div class="platform-icon" style="background: ${isCompatible ? platform.color : "#9ca3af"}">
          <i class="${platform.icon}"></i>
        </div>
        <div>
          <div class="platform-name">${platform.name}</div>
          <div style="font-size: 0.75rem; color: ${isCompatible ? "#6b7280" : "#ef4444"};">
            ${
              isCompatible
                ? `${accounts.length} account${accounts.length > 1 ? "s" : ""}`
                : "Not compatible with current content"
            }
          </div>
        </div>
        ${!isCompatible ? '<div class="compatibility-warning"><i class="fas fa-exclamation-triangle"></i></div>' : ""}
      `

      if (isCompatible) {
        platformCard.addEventListener("click", () => this.togglePlatform(key, platformCard))
      }
      this.platformsGrid.appendChild(platformCard)
    })
  }

  togglePlatform(platformKey, element) {
    if (this.selectedPlatforms.has(platformKey)) {
      this.selectedPlatforms.delete(platformKey)
      element.classList.remove("selected")
    } else {
      this.selectedPlatforms.add(platformKey)
      element.classList.add("selected")
    }
  }

  updateCharCounter() {
    const count = this.postDescription.value.length
    this.charCounter.textContent = `${count} characters`
  }

  handleTagInput(e) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      const tag = this.tagInput.value.trim()
      if (tag && !this.tags.includes(tag)) {
        this.addTag(tag)
        this.tagInput.value = ""
      }
    }
  }

  addTag(tag) {
    this.tags.push(tag)
    this.renderTags()
  }

  removeTag(tag) {
    this.tags = this.tags.filter((t) => t !== tag)
    this.renderTags()
  }

  renderTags() {
    const existingTags = this.tagsContainer.querySelectorAll(".tag")
    existingTags.forEach((tag) => tag.remove())

    this.tags.forEach((tag) => {
      const tagElement = document.createElement("div")
      tagElement.className = "tag"
      tagElement.innerHTML = `
                ${tag}
                <span class="tag-remove" onclick="composer.removeTag('${tag}')">&times;</span>
            `
      this.tagsContainer.insertBefore(tagElement, this.tagInput)
    })
  }

  handleFileUpload(e) {
    const files = Array.from(e.target.files)
    this.addFiles(files)
  }

  handleDragOver(e) {
    e.preventDefault()
    this.uploadArea.style.borderColor = "#667eea"
  }

  handleFileDrop(e) {
    e.preventDefault()
    this.uploadArea.style.borderColor = "#d1d5db"
    const files = Array.from(e.dataTransfer.files)
    this.addFiles(files)
  }

  addFiles(files) {
    files.forEach((file) => {
      if (!this.uploadedFiles.find((f) => f.name === file.name && f.size === file.size)) {
        this.uploadedFiles.push(file)
      }
    })
    this.renderFilePreview()
    this.renderPlatforms() // Re-render to update compatibility
  }

  removeFile(index) {
    this.uploadedFiles.splice(index, 1)
    this.renderFilePreview()
    this.renderPlatforms() // Re-render to update compatibility
  }

  renderFilePreview() {
    this.filePreview.innerHTML = ""

    this.uploadedFiles.forEach((file, index) => {
      const fileItem = document.createElement("div")
      fileItem.className = "file-item"

      if (file.type.startsWith("image/")) {
        const img = document.createElement("img")
        img.src = URL.createObjectURL(file)
        img.style.width = "100%"
        img.style.height = "120px"
        img.style.objectFit = "cover"
        fileItem.appendChild(img)
      } else {
        fileItem.innerHTML = `
                    <div style="padding: 1rem; text-align: center;">
                        <i class="fas fa-file" style="font-size: 2rem; color: #6b7280; margin-bottom: 0.5rem;"></i>
                        <div style="font-size: 0.875rem; color: #374151; word-break: break-all;">${file.name}</div>
                    </div>
                `
      }

      const removeBtn = document.createElement("button")
      removeBtn.className = "file-remove"
      removeBtn.innerHTML = "&times;"
      removeBtn.onclick = () => this.removeFile(index)
      fileItem.appendChild(removeBtn)

      this.filePreview.appendChild(fileItem)
    })
  }

  showAccountSelection() {
    if (this.selectedPlatforms.size === 0) {
      alert("Please select at least one platform to post to.")
      return
    }

    this.renderAccountSelection()
    this.accountSelectionModal.classList.add("active")
  }

  hideAccountSelection() {
    this.accountSelectionModal.classList.remove("active")
  }

  renderAccountSelection() {
    console.log("[debug] === RENDERING ACCOUNT SELECTION ===")
    this.platformsList.innerHTML = ""
    this.selectedAccounts.clear()

    Array.from(this.selectedPlatforms).forEach((platformKey) => {
      const platform = platformCompatibility[platformKey]
      const accounts = platformAccounts[platformKey] || []

      console.log(`[debug] Rendering ${platformKey} with ${accounts.length} accounts`)

      const platformSection = document.createElement("div")
      platformSection.className = "platform-section"

      platformSection.innerHTML = `
        <div class="platform-header">
          <div class="platform-icon" style="background: ${platform.color}">
            <i class="${platform.icon}"></i>
          </div>
          <h3>${platform.name}</h3>
        </div>
        <div class="accounts-list" data-platform="${platformKey}">
          ${accounts
            .map((account, index) => {
              let displayName, username, accountId

              console.log(`[debug] Processing account ${index} for ${platformKey}:`, account)

              switch (platformKey) {
                case "yt_acc":
                  displayName = account.channel_title
                  username = `@${account.channel_title}`
                  accountId = account.channel_id
                  break
                case "meta_acc":
                  displayName = account.account_name
                  username = account.username
                  accountId = account.account_id
                  break
                case "linkedin_acc":
                  displayName = account.name
                  username = account.username
                  accountId = account.linkedin_id
                  break
                case "thread_acc":
                  displayName = account.name
                  username = account.username
                  accountId = account.account_id
                  break
                case "tiktok_acc":
                  displayName = account.display_name
                  username = account.username
                  accountId = account.tiktok_id
                  break
                case "x_acc":
                  displayName = account.name
                  username = account.username
                  accountId = account.x_id
                  break
                default:
                  displayName = account.name || account.account_name || account.display_name
                  username = account.username
                  accountId = account.id
              }

              console.log(`[debug] Extracted for ${platformKey}[${index}]:`, {
                displayName,
                username,
                accountId,
                dataAccountId: accountId,
              })

              return `
                <div class="account-item" data-platform="${platformKey}" data-account-index="${index}" data-account-id="${accountId}">
                  <input type="checkbox" class="account-checkbox" id="account_${platformKey}_${index}">
                  <div class="account-info">
                    <div class="account-username">${username}</div>
                  </div>
                </div>
              `
            })
            .join("")}
        </div>
      `

      this.platformsList.appendChild(platformSection)
    })

    console.log("[debug] Created account items:")
    document.querySelectorAll(".account-item").forEach((item) => {
      console.log(`[debug] Account item:`, {
        platform: item.dataset.platform,
        accountIndex: item.dataset.accountIndex,
        accountId: item.dataset.accountId,
      })
    })
    console.log("[debug] === END RENDERING ACCOUNT SELECTION ===")

    // Bind account selection events
    this.platformsList.addEventListener("click", (e) => {
      const accountItem = e.target.closest(".account-item")
      if (accountItem) {
        const checkbox = accountItem.querySelector(".account-checkbox")
        const platform = accountItem.dataset.platform
        const accountIndex = Number.parseInt(accountItem.dataset.accountIndex)

        checkbox.checked = !checkbox.checked
        accountItem.classList.toggle("selected", checkbox.checked)

        if (checkbox.checked) {
          if (!this.selectedAccounts.has(platform)) {
            this.selectedAccounts.set(platform, [])
          }
          this.selectedAccounts.get(platform).push(accountIndex)
        } else {
          const accounts = this.selectedAccounts.get(platform) || []
          const index = accounts.indexOf(accountIndex)
          if (index > -1) {
            accounts.splice(index, 1)
          }
          if (accounts.length === 0) {
            this.selectedAccounts.delete(platform)
          }
        }
      }
    })
  }

  startPosting() {
    if (this.selectedAccounts.size === 0) {
      alert("Please select at least one account to post to.")
      return
    }

    this.hideAccountSelection()
    this.showPostingProgress()
    this.executePosting()
  }

  showPostingProgress() {
    this.renderPostingProgress()
    this.postingProgressModal.classList.add("active")
  }

  hidePostingProgress() {
    this.postingProgressModal.classList.remove("active")
  }

  renderPostingProgress() {
    this.progressList.innerHTML = ""
    this.closeProgressModal.style.display = "none"

    // Create progress items for each selected account
    this.selectedAccounts.forEach((accountIndices, platformKey) => {
      const platform = platformCompatibility[platformKey]
      const accounts = platformAccounts[platformKey]

      accountIndices.forEach((accountIndex) => {
        const account = accounts[accountIndex]
        const progressItem = document.createElement("div")
        progressItem.className = "progress-item"
        progressItem.dataset.platform = platformKey
        progressItem.dataset.accountIndex = accountIndex

        let displayName, username
        switch (platformKey) {
          case "yt_acc":
            displayName = account.channel_title || account.name || "Unknown Channel"
            username = account.channel_title || account.username || "Unknown"
            break
          case "meta_acc":
            displayName = account.account_name || account.name || "Unknown Account"
            username = account.username || "Unknown"
            break
          case "linkedin_acc":
            displayName = account.name || "Unknown Account"
            username = account.username || "Unknown"
            break
          case "thread_acc":
            displayName = account.name || "Unknown Account"
            username = account.username || "Unknown"
            break
          case "tiktok_acc":
            displayName = account.display_name || account.name || "Unknown Account"
            username = account.username || "Unknown"
            break
          case "x_acc":
            displayName = account.name || "Unknown Account"
            username = account.username || "Unknown"
            break
          default:
            displayName = account.name || account.account_name || account.display_name || "Unknown Account"
            username = account.username || "Unknown"
        }

        console.log("[debug] Creating progress item for:", platformKey, accountIndex, displayName)

        progressItem.innerHTML = `
                    <div class="progress-icon" style="background: ${platform.color}">
                        <i class="${platform.icon}"></i>
                    </div>
                    <div class="progress-info">
                        <div class="progress-platform">${platform.name}</div>
                        <div class="progress-account">${displayName} (${username})</div>
                        <div class="progress-status">
                            <div class="status-indicator pending"></div>
                            <span class="status-text pending">Preparing...</span>
                            <div class="spinner" style="margin-left: 0.5rem;"></div>
                        </div>
                    </div>
                `

        this.progressList.appendChild(progressItem)
      })
    })

    console.log("[debug] Created progress items:", document.querySelectorAll(".progress-item").length)
    document.querySelectorAll(".progress-item").forEach((item) => {
      console.log("[debug] Progress item:", item.dataset.platform, item.dataset.accountIndex)
    })
  }

  async executePosting() {
    const postData = {
      title: this.postTitle.value,
      description: this.postDescription.value,
      tags: this.tags.join(","),
      media_files: this.uploadedFiles,
    }

    let allCompleted = 0
    let successfulPosts = 0
    const totalPosts = Array.from(this.selectedAccounts.values()).reduce((sum, accounts) => sum + accounts.length, 0)

    const postResults = []

    // Process each platform and account
    for (const [platformKey, accountIndices] of this.selectedAccounts) {
      const platform = platformCompatibility[platformKey]
      const accounts = platformAccounts[platformKey]

      for (const accountIndex of accountIndices) {
        const account = accounts[accountIndex]
        const progressItem = document.querySelector(
          `[data-platform="${platformKey}"][data-account-index="${accountIndex}"]`,
        )

        console.log(
          "[debug] Looking for progress item with selector:",
          `[data-platform="${platformKey}"][data-account-index="${accountIndex}"]`,
        )
        console.log("[debug] Found progress item:", progressItem)

        if (!progressItem) {
          console.log("[debug] ERROR: Could not find progress item for", platformKey, accountIndex)
          console.log("[debug] Available progress items:", document.querySelectorAll(".progress-item"))
          allCompleted++
          continue
        }

        try {
          const success = await this.postToAccount(platformKey, account, postData, progressItem)

          let displayName, username
          switch (platformKey) {
            case "yt_acc":
              displayName = account.channel_title || account.name || "Unknown Channel"
              username = account.channel_title || account.username || "Unknown"
              break
            case "meta_acc":
              displayName = account.account_name || account.name || "Unknown Account"
              username = account.username || "Unknown"
              break
            case "linkedin_acc":
              displayName = account.name || "Unknown Account"
              username = account.username || "Unknown"
              break
            case "thread_acc":
              displayName = account.name || "Unknown Account"
              username = account.username || "Unknown"
              break
            case "tiktok_acc":
              displayName = account.display_name || account.name || "Unknown Account"
              username = account.username || "Unknown"
              break
            case "x_acc":
              displayName = account.name || "Unknown Account"
              username = account.username || "Unknown"
              break
            default:
              displayName = account.name || account.account_name || account.display_name || "Unknown Account"
              username = account.username || "Unknown"
          }

          postResults.push({
            platform: platform.name,
            platformKey: platformKey,
            account: displayName,
            username: username,
            success: success,
            icon: platform.icon,
            color: platform.color,
          })

          if (success) {
            successfulPosts++
          }
        } catch (error) {
          this.updateProgressStatus(progressItem, "error", `Failed: ${error.message}`, true)

          postResults.push({
            platform: platform.name,
            platformKey: platformKey,
            account: "Unknown Account",
            username: "Unknown",
            success: false,
            error: error.message,
            icon: platform.icon,
            color: platform.color,
          })
        }

        allCompleted++
      }
    }

    if (allCompleted === totalPosts) {
      setTimeout(() => {
        this.showPostingSummary(postResults, successfulPosts, totalPosts)
      }, 1000)
    }
  }

  showPostingSummary(results, successCount, totalCount) {
    // Hide the progress modal
    this.hidePostingProgress()

    // Hide all main content
    document.querySelector(".main-content").style.display = "none"
    document.querySelector(".header").style.display = "none"

    // Create summary modal
    const summaryModal = document.createElement("div")
    summaryModal.className = "modal-overlay active"
    summaryModal.style.zIndex = "10000"
    summaryModal.innerHTML = `
      <div class="modal-content" style="max-width: 600px; max-height: 80vh; overflow-y: auto;">
        <div class="modal-header" style="text-align: center; border-bottom: 2px solid #e5e7eb; padding-bottom: 1rem;">
          <h2 style="margin: 0; color: ${successCount === totalCount ? "#10b981" : "#ef4444"};">
            <i class="fas ${successCount === totalCount ? "fa-check-circle" : "fa-exclamation-triangle"}" style="margin-right: 0.5rem;"></i>
            Posting Complete
          </h2>
          <p style="margin: 0.5rem 0 0 0; color: #6b7280;">
            ${successCount} of ${totalCount} posts successful
          </p>
        </div>
        <div class="modal-body" style="padding: 1.5rem 0;">
          <div class="summary-stats" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem;">
            <div style="text-align: center; padding: 1rem; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;">
              <div style="font-size: 2rem; font-weight: bold; color: #10b981;">${successCount}</div>
              <div style="color: #059669; font-size: 0.875rem;">Successful</div>
            </div>
            <div style="text-align: center; padding: 1rem; background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca;">
              <div style="font-size: 2rem; font-weight: bold; color: #ef4444;">${totalCount - successCount}</div>
              <div style="color: #dc2626; font-size: 0.875rem;">Failed</div>
            </div>
          </div>
          <div class="results-list">
            ${results
              .map(
                (result) => `
              <div class="result-item" style="display: flex; align-items: center; padding: 1rem; margin-bottom: 0.5rem; border-radius: 8px; background: ${result.success ? "#f0fdf4" : "#fef2f2"}; border: 1px solid ${result.success ? "#bbf7d0" : "#fecaca"};">
                <div class="result-icon" style="background: ${result.color}; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 1rem;">
                  <i class="${result.icon}" style="color: white; font-size: 1.2rem;"></i>
                </div>
                <div class="result-info" style="flex: 1;">
                  <div style="font-weight: 600; color: #374151;">${result.platform}</div>
                  <div style="font-size: 0.875rem; color: #6b7280;">${result.account} (${result.username})</div>
                  ${result.error ? `<div style="font-size: 0.75rem; color: #ef4444; margin-top: 0.25rem;">${result.error}</div>` : ""}
                </div>
                <div class="result-status">
                  <i class="fas ${result.success ? "fa-check-circle" : "fa-times-circle"}" style="color: ${result.success ? "#10b981" : "#ef4444"}; font-size: 1.5rem;"></i>
                </div>
              </div>
            `,
              )
              .join("")}
          </div>
        </div>
        <div class="modal-footer" style="border-top: 2px solid #e5e7eb; padding-top: 1rem; display: flex; gap: 1rem; justify-content: center;">
          <button class="btn btn-primary" onclick="window.location.href='/'" style="padding: 0.75rem 1.5rem;">
            <i class="fas fa-home" style="margin-right: 0.5rem;"></i>
            Go Home
          </button>
        </div>
      </div>
    `

    document.body.appendChild(summaryModal)
  }

  async postToAccount(platformKey, account, postData, progressItem) {
    const platform = platformCompatibility[platformKey]

    // Update status to posting
    this.updateProgressStatus(progressItem, "pending", "Posting...")

    console.log("[debug] === POSTING TO ACCOUNT ===")
    console.log("[debug] Platform:", platformKey)
    console.log("[debug] Account object:", account)
    console.log("[debug] Account properties:", Object.keys(account))

    // Prepare form data based on platform
    const formData = new FormData()
    const extractedId = account.id

    console.log("[debug] Using account.id for all platforms:", extractedId)

    switch (platformKey) {
      case "meta_acc":
        formData.append("account_id", extractedId)
        formData.append("platforms", "facebook,instagram")
        break
      case "yt_acc":
        formData.append("channel_id", extractedId)
        formData.append("privacy_status", "public")
        break
      case "x_acc":
        formData.append("x_account_id", extractedId)
        break
      case "tiktok_acc":
        formData.append("tiktok_account_id", extractedId)
        formData.append("privacy_level", "PUBLIC_TO_EVERYONE")
        break
      case "linkedin_acc":
        formData.append("linkedin_id", extractedId)
        break
      case "thread_acc":
        formData.append("threads_account_id", extractedId)
        break
    }

    console.log("[debug] Extracted ID for", platformKey, ":", extractedId)
    console.log("[debug] ID is undefined:", extractedId === undefined)
    console.log("[debug] ID is null:", extractedId === null)

    // Add common data
    formData.append("title", postData.title)
    formData.append("description", postData.description)
    formData.append("tags", postData.tags)

    postData.media_files.forEach((file) => {
      if (platformKey === "yt_acc" || platformKey === "tiktok_acc") {
        formData.append("video_file", file)
      } else if (platformKey === "linkedin_acc") {
        formData.append("media_file", file) // LinkedIn only supports single file
      } else {
        formData.append("media_files", file)
      }
    })

    const csrfToken = this.getCsrfToken()
    console.log("[debug] CSRF token found:", csrfToken ? "Yes" : "No")

    if (!csrfToken) {
      throw new Error("CSRF token not found. Please refresh the page.")
    }

    try {
      console.log("[debug] Making fetch request to", platform.endpoint)
      console.log("[debug] FormData contents:")
      for (const [key, value] of formData.entries()) {
        if (value instanceof File) {
          console.log(`[debug] ${key}: File(${value.name}, ${value.size} bytes)`)
        } else {
          console.log(`[debug] ${key}: ${value}`)
        }
      }

      const response = await fetch(platform.endpoint, {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": csrfToken,
        },
      })

      console.log("[debug] Response status:", response.status)
      console.log("[debug] Response ok:", response.ok)

      let result
      try {
        const responseText = await response.text()
        console.log("[debug] Raw response text:", responseText)

        if (responseText.trim()) {
          result = JSON.parse(responseText)
          console.log("[debug] Parsed response data:", result)
        } else {
          throw new Error("Empty response from server")
        }
      } catch (jsonError) {
        console.log("[debug] Failed to parse JSON response:", jsonError)
        throw new Error(`Server returned invalid response. Status: ${response.status}`)
      }

      console.log("[debug] Checking success conditions:")
      console.log("[debug] response.ok:", response.ok)
      console.log("[debug] result.success:", result.success)
      console.log("[debug] result.message:", result.message)
      console.log("[debug] result.error:", result.error)

      const isSuccess =
        response.ok &&
        (result.success === true ||
          result.success === "True" ||
          result.success === "true" ||
          (result.message && !result.error && response.status === 200))

      if (isSuccess) {
        console.log("[debug] SUCCESS: Updating progress to success")
        this.updateProgressStatus(progressItem, "success", "Posted successfully!")
        console.log("[debug] SUCCESS: Progress status updated")
        return true // Return success indicator
      } else {
        const errorMessage = result.error || result.message || `HTTP ${response.status}: ${response.statusText}`
        console.log("[debug] ERROR: API error:", errorMessage)
        console.log("[debug] ERROR: Updating progress to error")
        this.updateProgressStatus(progressItem, "error", `Failed: ${errorMessage}`, true)
        return false // Return failure indicator
      }
    } catch (error) {
      console.log("[debug] CATCH: Fetch error:", error)
      console.log("[debug] CATCH: Updating progress to error")
      this.updateProgressStatus(progressItem, "error", `Failed: ${error.message}`, true)
      return false // Return failure indicator
    }
  }

  updateProgressStatus(progressItem, status, message, showRetry = false) {
    console.log("[debug] === UPDATE PROGRESS STATUS ===")
    console.log("[debug] progressItem:", progressItem)
    console.log("[debug] status:", status)
    console.log("[debug] message:", message)
    console.log("[debug] showRetry:", showRetry)

    if (!progressItem) {
      console.log("[debug] ERROR: progressItem is null in updateProgressStatus")
      return
    }

    const statusIndicator = progressItem.querySelector(".status-indicator")
    const statusText = progressItem.querySelector(".status-text")
    const spinner = progressItem.querySelector(".spinner")
    const existingRetryBtn = progressItem.querySelector(".retry-btn")

    console.log("[debug] Found elements:")
    console.log("[debug] statusIndicator:", statusIndicator)
    console.log("[debug] statusText:", statusText)
    console.log("[debug] spinner:", spinner)

    if (!statusIndicator) {
      console.log("[debug] ERROR: status-indicator element not found")
      console.log("[debug] progressItem HTML:", progressItem.innerHTML)
      return
    }
    if (!statusText) {
      console.log("[debug] ERROR: status-text element not found")
      console.log("[debug] progressItem HTML:", progressItem.innerHTML)
      return
    }

    requestAnimationFrame(() => {
      // Remove spinner
      if (spinner) {
        console.log("[debug] Removing spinner")
        spinner.remove()
      }

      // Remove existing retry button
      if (existingRetryBtn) {
        console.log("[debug] Removing existing retry button")
        existingRetryBtn.remove()
      }

      // Update status indicator and text
      console.log("[debug] Updating status indicator class to:", `status-indicator ${status}`)
      console.log("[debug] Updating status text class to:", `status-text ${status}`)
      console.log("[debug] Updating status text content to:", message)

      statusIndicator.className = `status-indicator ${status}`
      statusText.className = `status-text ${status}`
      statusText.textContent = message

      statusIndicator.style.display = "none"
      statusIndicator.offsetHeight // Trigger reflow
      statusIndicator.style.display = ""

      console.log("[debug] Status updated successfully")

      // Add retry button if needed
      if (showRetry) {
        console.log("[debug] Adding retry button")
        const retryBtn = document.createElement("button")
        retryBtn.className = "retry-btn"
        retryBtn.textContent = "Retry"
        retryBtn.style.marginLeft = "1rem"

        retryBtn.addEventListener("click", async () => {
          const platformKey = progressItem.dataset.platform
          const accountIndex = Number.parseInt(progressItem.dataset.accountIndex)
          const platform = platformCompatibility[platformKey]
          const account = platformAccounts[platformKey][accountIndex]

          const postData = {
            title: this.postTitle.value,
            description: this.postDescription.value,
            tags: this.tags.join(","),
            media_files: this.uploadedFiles,
          }

          // Add spinner back
          const newSpinner = document.createElement("div")
          newSpinner.className = "spinner"
          newSpinner.style.marginLeft = "0.5rem"
          statusText.parentNode.appendChild(newSpinner)

          retryBtn.remove()

          try {
            await this.postToAccount(platformKey, account, postData, progressItem)
          } catch (error) {
            this.updateProgressStatus(progressItem, "error", `Failed: ${error.message}`, true)
          }
        })

        statusText.parentNode.appendChild(retryBtn)
      }
    })

    console.log("[debug] === END UPDATE PROGRESS STATUS ===")
  }

  getCsrfToken() {
    let csrfToken = null

    // Method 1: Look for CSRF token in hidden input (Django's {% csrf_token %} creates this)
    const inputToken = document.querySelector('input[name="csrfmiddlewaretoken"]')
    if (inputToken) {
      csrfToken = inputToken.value
      console.log("[debug] CSRF token found in hidden input:", csrfToken.substring(0, 10) + "...")
    }

    // Method 2: Look for CSRF token in meta tag (Django's recommended approach)
    if (!csrfToken) {
      const metaToken = document.querySelector('meta[name="csrf-token"]')
      if (metaToken) {
        csrfToken = metaToken.getAttribute("content")
        console.log("[debug] CSRF token found in meta tag:", csrfToken.substring(0, 10) + "...")
      }
    }

    // Method 3: Look for CSRF token in cookies (if Django is configured to use cookies)
    if (!csrfToken) {
      const cookies = document.cookie.split(";")
      for (const cookie of cookies) {
        const [name, value] = cookie.trim().split("=")
        if (name === "csrftoken") {
          csrfToken = value
          console.log("[debug] CSRF token found in cookies:", csrfToken.substring(0, 10) + "...")
          break
        }
      }
    }

    if (!csrfToken) {
      console.log("[debug] CSRF token NOT FOUND - checking available elements:")
      console.log("[debug] Hidden inputs:", document.querySelectorAll('input[type="hidden"]'))
      console.log("[debug] Meta tags:", document.querySelectorAll("meta"))
      console.log("[debug] Cookies:", document.cookie)
    }

    return csrfToken || ""
  }

  checkPlatformCompatibility(platformKey) {
    const platform = platformCompatibility[platformKey]
    const hasText = this.postTitle.value.trim() || this.postDescription.value.trim()
    const hasImages = this.uploadedFiles.some((file) => file.type.startsWith("image/"))
    const hasVideos = this.uploadedFiles.some((file) => file.type.startsWith("video/"))
    const fileCount = this.uploadedFiles.length

    // Check if platform supports the content type
    if (!hasText && !hasImages && !hasVideos) {
      return platform.requirements.text // Can post text-only
    }

    if (hasText && !hasImages && !hasVideos) {
      return platform.requirements.text
    }

    if (hasImages && !hasVideos) {
      return platform.requirements.image
    }

    if (hasVideos) {
      if (!platform.requirements.video) return false

      // Check video file formats and sizes
      for (const file of this.uploadedFiles.filter((f) => f.type.startsWith("video/"))) {
        const extension = file.name.split(".").pop().toLowerCase()
        if (!platform.requirements.videoFormats.includes(extension)) return false

        // Size check (simplified - would need actual size limits)
        const maxSizeMB = this.parseSize(platform.requirements.videoMaxSize)
        if (file.size > maxSizeMB * 1024 * 1024) return false
      }
    }

    // Check file count limits
    if (fileCount > platform.requirements.maxFiles) return false

    // Special case for Instagram (Meta) - requires media
    if (platformKey === "meta_acc" && !hasImages && !hasVideos) {
      return platform.requirements.text.facebook // Only Facebook allows text-only
    }

    return true
  }

  parseSize(sizeStr) {
    const units = { MB: 1, GB: 1024, TB: 1024 * 1024 }
    const match = sizeStr.match(/(\d+)(MB|GB|TB)/)
    if (!match) return 0
    return Number.parseInt(match[1]) * units[match[2]]
  }
}

// Initialize the composer when DOM is loaded
let composer
document.addEventListener("DOMContentLoaded", () => {
  composer = new ComposerApp()
})
