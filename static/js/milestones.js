/**
 * Milestone Progress Module
 * Handles badge display and progress bar updates via API
 */

// Constants
const BADGE_COLORS = {
    BRONZE: '#CD7F32',
    SILVER: '#A8A8A8',
    GOLD: '#FFA500'
};

const GRADIENT_PRESETS = {
    [BADGE_COLORS.BRONZE]: {
        start: '#E6A55C',
        mid: '#CD7F32',
        end: '#A0522D'
    },
    [BADGE_COLORS.SILVER]: {
        start: '#D3D3D3',
        mid: '#A8A8A8',
        end: '#808080'
    },
    [BADGE_COLORS.GOLD]: {
        start: '#FFD700',
        mid: '#FFA500',
        end: '#FF8C00'
    }
};

const PROGRESS_RING = {
    RADIUS: 60,
    CENTER_X: 70,
    CENTER_Y: 70,
    COLOR_ADJUSTMENT: 30
};

const INIT_DELAY = 300;

/**
 * Convert hex color to RGB object
 * @param {string} hex - Hex color string (with or without #)
 * @returns {{r: number, g: number, b: number}|null} RGB object or null if invalid
 */
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

/**
 * Generate gradient colors for a badge
 * @param {string} badgeColor - Base badge color in hex format
 * @returns {{start: string, mid: string, end: string}} Gradient color stops
 */
function generateGradientColors(badgeColor) {
    // Check if we have a preset gradient
    if (GRADIENT_PRESETS[badgeColor]) {
        return GRADIENT_PRESETS[badgeColor];
    }

    // Generate gradient from base color
    const rgb = hexToRgb(badgeColor);
    if (!rgb) {
        // Fallback: return same color for all stops
        return {
            start: badgeColor,
            mid: badgeColor,
            end: badgeColor
        };
    }

    return {
        start: `rgb(${Math.min(255, rgb.r + PROGRESS_RING.COLOR_ADJUSTMENT)}, ${Math.min(255, rgb.g + PROGRESS_RING.COLOR_ADJUSTMENT)}, ${Math.min(255, rgb.b + PROGRESS_RING.COLOR_ADJUSTMENT)})`,
        mid: badgeColor,
        end: `rgb(${Math.max(0, rgb.r - PROGRESS_RING.COLOR_ADJUSTMENT)}, ${Math.max(0, rgb.g - PROGRESS_RING.COLOR_ADJUSTMENT)}, ${Math.max(0, rgb.b - PROGRESS_RING.COLOR_ADJUSTMENT)})`
    };
}

/**
 * Create CSS gradient string
 * @param {string} badgeColor - Base badge color
 * @returns {string} CSS linear-gradient string
 */
function createGradient(badgeColor) {
    const colors = generateGradientColors(badgeColor);
    return `linear-gradient(135deg, ${colors.start} 0%, ${colors.mid} 50%, ${colors.end} 100%)`;
}

/**
 * Apply icon styles to ensure white color
 * @param {HTMLElement} icon - Icon element
 */
function applyWhiteIconStyles(icon) {
    if (!icon) return;
    
    icon.setAttribute('style', `
        color: #ffffff !important;
        fill: #ffffff !important;
        stroke: #ffffff !important;
        stroke-width: 2px !important;
    `);
    icon.classList.remove('text-gray-400');
    icon.classList.add('text-white');
}

/**
 * Apply gray icon styles for default state
 * @param {HTMLElement} icon - Icon element
 */
function applyGrayIconStyles(icon) {
    if (!icon) return;
    
    icon.setAttribute('style', `
        color: #9ca3af !important;
        stroke: none !important;
        stroke-width: 0 !important;
    `);
    icon.classList.add('text-gray-400');
}

const MilestoneModule = {
    /**
     * Initialize milestone module
     */
    init() {
        const badgeContainer = document.getElementById('milestone-badge-container');
        const profileBadgeContainer = document.getElementById('badge-container');
        
        if (!badgeContainer && !profileBadgeContainer) {
            return;
        }

        const initFunction = () => {
            setTimeout(() => {
                this.updateMilestoneProgress();
            }, INIT_DELAY);
            
            // Refresh milestone progress periodically (every 30 seconds) to catch new milestones
            // This ensures the badge updates when a new milestone is reached
            setInterval(() => {
                this.updateMilestoneProgress();
            }, 30000); // 30 seconds
            
            // Refresh when page becomes visible (user switches back to tab)
            // This ensures badge updates if user completes an order in another tab
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) {
                    // Page became visible, refresh milestone progress
                    setTimeout(() => {
                        this.updateMilestoneProgress();
                    }, 500);
                }
            });
        };
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initFunction);
        } else {
            initFunction();
        }
    },

    /**
     * Update milestone progress badge and progress bar
     */
    async updateMilestoneProgress() {
        try {
            const response = await fetch('/vouchers/api/milestone-progress/');
            
            if (!response.ok) {
                this.hideAllBadges();
                return;
            }

            const data = await response.json();
            
            if (data.success && data.milestone_progress) {
                this.updateBadge(data.milestone_progress);
                this.updateProgressBar(data.milestone_progress);
                this.updateProfileBadge(data.milestone_progress);
            } else {
                this.hideAllBadges();
            }
        } catch (error) {
            console.error('Error fetching milestone progress:', error);
            this.hideAllBadges();
        }
    },

    /**
     * Hide all badge elements
     */
    hideAllBadges() {
        const badgeButton = document.getElementById('milestone-badge-button');
        const badgeContainer = document.getElementById('badge-container');
        
        if (badgeButton) {
            badgeButton.classList.add('hidden');
        }
        if (badgeContainer) {
            badgeContainer.classList.add('hidden');
        }
    },

    /**
     * Update badge in navbar dropdown
     * @param {Object} progress - Progress data object
     */
    updateBadge(progress) {
        const badgeButton = document.getElementById('milestone-badge-button');
        const badgeContainer = document.getElementById('milestone-badge-container');
        
        if (!badgeButton || !badgeContainer) {
            return;
        }

        const { current_badge: currentBadge, next_badge: nextBadge } = progress;

        if (!currentBadge && !nextBadge) {
            badgeButton.classList.add('hidden');
            return;
        }

        badgeButton.classList.remove('hidden');
        
        let badgeHTML = '';
        
        if (currentBadge) {
            const gradient = createGradient(currentBadge.color);
            badgeHTML = `
                <div class="badge-icon-nav-small" style="background: ${gradient}; box-shadow: 0 2px 6px ${currentBadge.color}40;">
                    <i data-lucide="award" class="w-4 h-4 text-white"></i>
                </div>
            `;
        } else {
            badgeHTML = '<i data-lucide="award" class="w-4 h-4 text-gray-400"></i>';
        }

        badgeContainer.innerHTML = badgeHTML;
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    },

    /**
     * Update circular progress bar in profile page
     * @param {Object} progress - Progress data object
     */
    updateProgressBar(progress) {
        const progressRing = document.querySelector('.progress-ring-fill');
        const progressBg = document.querySelector('.progress-ring-bg');
        const indicator = document.querySelector('.progress-indicator');
        
        if (!progressRing || !progressBg) {
            return;
        }

        const { next_badge: nextBadge, progress_percentage: progressPercent = 0 } = progress;
        
        // Calculate circumference and offset
        const circumference = 2 * Math.PI * PROGRESS_RING.RADIUS;
        const offset = circumference - (progressPercent / 100 * circumference);
        
        progressRing.setAttribute('stroke-dashoffset', progress.circular_offset || offset);
        progressRing.setAttribute('stroke', 'url(#gradient-fill)');
        progressRing.setAttribute('stroke-width', '10');
        progressRing.style.opacity = '1';
        progressBg.style.opacity = '0.3';
        
        // Update indicator position
        if (indicator && progressPercent > 0 && nextBadge) {
            const angle = -90 + (progressPercent / 100 * 360);
            const radian = (angle * Math.PI) / 180;
            const x = PROGRESS_RING.CENTER_X + PROGRESS_RING.RADIUS * Math.cos(radian);
            const y = PROGRESS_RING.CENTER_Y + PROGRESS_RING.RADIUS * Math.sin(radian);
            
            indicator.setAttribute('cx', x);
            indicator.setAttribute('cy', y);
            indicator.setAttribute('r', '6');
            indicator.setAttribute('fill', '#ffffff');
            indicator.style.opacity = '1';
            indicator.style.stroke = '#667eea';
            indicator.style.strokeWidth = '2';
            indicator.style.transform = 'translate(0, 0)';
        } else if (indicator) {
            indicator.style.opacity = '0';
        }
    },

    /**
     * Update badge icon in profile page
     * @param {Object} progress - Progress data object
     */
    updateProfileBadge(progress) {
        const badgeContainer = document.getElementById('badge-container');
        if (!badgeContainer) {
            return;
        }
        
        // Try multiple selectors to find the badge icon
        let badgeIcon = document.getElementById('badge-icon-profile');
        if (!badgeIcon) {
            badgeIcon = badgeContainer.querySelector('.badge-icon-large-profile');
        }
        if (!badgeIcon) {
            badgeIcon = badgeContainer.querySelector('[id*="badge"]');
        }
        
        const { current_badge: currentBadge, next_badge: nextBadge } = progress;

        badgeContainer.style.opacity = '1';
        badgeContainer.style.display = 'block';
        badgeContainer.style.visibility = 'visible';

        if (!badgeIcon) {
            return;
        }

        // Store previous badge info to detect changes
        const previousBadgeName = badgeIcon.getAttribute('data-badge-name');
        const currentBadgeName = currentBadge ? currentBadge.name : null;
        const badgeChanged = previousBadgeName !== currentBadgeName;

        badgeIcon.className = 'badge-icon-large-profile';
        
        // Clear all children (remove any existing icons and SVGs that lucide created)
        badgeIcon.innerHTML = '';
        
        // Determine icon to use - use badge icon if available, otherwise default to 'award'
        const iconName = currentBadge ? (currentBadge.icon || 'award') : 'award';
        
        // Create a single icon element
        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', iconName);
        icon.className = 'w-12 h-12 text-white';
        badgeIcon.appendChild(icon);
        
        // Initialize lucide icons - scope it to only this badge icon to prevent duplicates
        if (typeof lucide !== 'undefined') {
            // Process only this specific element to avoid global reprocessing
            lucide.createIcons(badgeIcon);
            
            // Safety check: if somehow we have multiple children, keep only the first SVG
            // Wait a bit for lucide to process, then clean up
            setTimeout(() => {
                if (badgeIcon.children.length > 1) {
                    const svgElement = badgeIcon.querySelector('svg');
                    if (svgElement) {
                        badgeIcon.innerHTML = '';
                        badgeIcon.appendChild(svgElement);
                    } else {
                        // If no SVG, keep only the first child
                        while (badgeIcon.children.length > 1) {
                            badgeIcon.removeChild(badgeIcon.lastChild);
                        }
                    }
                }
            }, 100);
        }

        if (currentBadge) {
            const gradient = createGradient(currentBadge.color);
            
            badgeIcon.style.cssText = `
                background: ${gradient} !important;
                border-color: ${currentBadge.color} !important;
                border-width: 3px !important;
                box-shadow: 0 8px 20px ${currentBadge.color}40, 0 2px 6px rgba(0, 0, 0, 0.1) !important;
                width: 100px !important;
                height: 100px !important;
                border-radius: 50% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: none !important;
            `;
            
            // Store current badge name for change detection
            badgeIcon.setAttribute('data-badge-name', currentBadge.name);
            badgeIcon.setAttribute('data-badge-color', currentBadge.color);
            
            applyWhiteIconStyles(icon);
        } else {
            // Show black badge when user has no badge
            const blackGradient = 'linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 50%, #000000 100%)';
            badgeIcon.style.cssText = `
                background: ${blackGradient} !important;
                border-color: #333333 !important;
                border-width: 3px !important;
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4), 0 2px 6px rgba(0, 0, 0, 0.3) !important;
                width: 100px !important;
                height: 100px !important;
                border-radius: 50% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: none !important;
            `;
            
            badgeIcon.removeAttribute('data-badge-name');
            badgeIcon.removeAttribute('data-badge-color');
            
            // Keep icon white for visibility on black background
            applyWhiteIconStyles(icon);
        }

        // Update next milestone info
        const nextInfo = document.getElementById('next-milestone-info');
        if (nextInfo) {
            if (nextBadge) {
                const voucherAmount = nextBadge.voucher_amount || 0;
                nextInfo.innerHTML = `
                    <span class="font-medium">Next: </span>
                    <span class="font-semibold" style="color: ${nextBadge.color};">${nextBadge.name}</span>
                    ${voucherAmount > 0 ? `<span class="text-green-600 font-semibold"> • $${voucherAmount.toFixed(2)} voucher</span>` : ''}
                    <span class="text-gray-400"> • </span>
                    <span>$${parseFloat(progress.current_amount).toFixed(2)}</span>
                    <span class="text-gray-400"> / </span>
                    <span class="font-semibold">$${parseFloat(progress.next_threshold).toFixed(2)}</span>
                `;
                nextInfo.classList.remove('hidden');
            } else {
                nextInfo.classList.add('hidden');
            }
        }
    },

    /**
     * Update modal content with milestone progress
     * @param {Object} progress - Progress data object
     */
    updateModalContent(progress) {
        const content = document.getElementById('milestone-modal-content');
        if (!content) {
            return;
        }

        const { current_badge: currentBadge, next_badge: nextBadge } = progress;
        let html = '';

        if (!currentBadge) {
            // Show black badge when user has no badge
            const blackGradient = 'linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 50%, #000000 100%)';
            html += `
                <div class="mb-8">
                    <h3 class="text-sm font-semibold text-gray-500 uppercase mb-3">Current Badge</h3>
                    <div class="flex items-center gap-4 p-4 rounded-xl" style="background: linear-gradient(135deg, #1a1a1a15 0%, #00000005 100%); border: 2px solid #333333;">
                        <div class="badge-icon-large" style="background: ${blackGradient}; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); border-color: #333333;">
                            <i data-lucide="award" class="w-12 h-12 text-white"></i>
                        </div>
                        <div class="flex-1">
                            <h4 class="text-xl font-bold text-gray-700">No Badge Yet</h4>
                            <p class="text-sm text-gray-600">Start shopping to earn your first badge!</p>
                            <p class="text-xs text-gray-500 mt-1">Total spending: $${parseFloat(progress.current_amount || 0).toFixed(2)}</p>
                        </div>
                    </div>
                </div>
            `;
        } else if (currentBadge) {
            const gradient = createGradient(currentBadge.color);
            const voucherAmount = currentBadge.voucher_amount || 0;
            const voucherReceived = currentBadge.voucher_received !== false; // Default to true if not specified
            
            html += `
                <div class="mb-8">
                    <h3 class="text-sm font-semibold text-gray-500 uppercase mb-3">Current Badge</h3>
                    <div class="flex items-center gap-4 p-4 rounded-xl" style="background: linear-gradient(135deg, ${currentBadge.color}15 0%, ${currentBadge.color}05 100%); border: 2px solid ${currentBadge.color};">
                        <div class="badge-icon-large" style="background: ${gradient}; box-shadow: 0 8px 20px ${currentBadge.color}40;">
                            <i data-lucide="${currentBadge.icon || 'award'}" class="w-12 h-12 text-white"></i>
                        </div>
                        <div class="flex-1">
                            <h4 class="text-xl font-bold" style="color: ${currentBadge.color};">${currentBadge.name}</h4>
                            <p class="text-sm text-gray-600">${currentBadge.description || ''}</p>
                            ${voucherAmount > 0 ? `
                                <div class="mt-2 flex items-center gap-2">
                                    <i data-lucide="gift" class="w-4 h-4 ${voucherReceived ? 'text-green-600' : 'text-yellow-600'}"></i>
                                    <span class="text-sm font-semibold ${voucherReceived ? 'text-green-600' : 'text-yellow-600'}">
                                        ${voucherReceived ? `Reward: $${voucherAmount.toFixed(2)} voucher received!` : `Reward: $${voucherAmount.toFixed(2)} voucher pending...`}
                                    </span>
                                </div>
                            ` : ''}
                            <p class="text-xs text-gray-500 mt-1">Total spending: $${parseFloat(progress.current_amount).toFixed(2)}</p>
                        </div>
                    </div>
                </div>
            `;
        }

        if (nextBadge) {
            const voucherAmount = nextBadge.voucher_amount || 0;
            const nextGradient = createGradient(nextBadge.color);
            
            html += `
                <div>
                    <h3 class="text-sm font-semibold text-gray-500 uppercase mb-3">Next Milestone</h3>
                    <div class="bg-gray-50 rounded-xl p-6 border-2 border-gray-200">
                        <div class="flex items-center gap-4 mb-4">
                            <div class="badge-icon-large" style="background: ${nextGradient}; box-shadow: 0 8px 20px ${nextBadge.color}40; border-color: ${nextBadge.color};">
                                <i data-lucide="${nextBadge.icon || 'award'}" class="w-12 h-12 text-white"></i>
                            </div>
                            <div class="flex-1">
                                <h4 class="text-xl font-bold text-gray-700">${nextBadge.name}</h4>
                                <p class="text-sm text-gray-600">${nextBadge.description || ''}</p>
                                ${voucherAmount > 0 ? `
                                    <div class="mt-2 flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                                        <i data-lucide="gift" class="w-4 h-4 text-green-600 flex-shrink-0"></i>
                                        <span class="text-sm font-semibold text-green-700">Earn a $${voucherAmount.toFixed(2)} voucher when you reach this milestone!</span>
                                    </div>
                                ` : ''}
                            </div>
                        </div>

                        <!-- Progress Bar -->
                        <div class="mb-4">
                            <div class="flex items-center justify-between text-sm mb-2">
                                <span class="text-gray-600 font-medium">Progress</span>
                                <span class="text-gray-900 font-bold">${progress.progress_percentage}%</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                                <div class="h-full rounded-full transition-all duration-1000 ease-out flex items-center justify-end pr-2" 
                                     style="width: ${progress.progress_percentage}%; background: linear-gradient(90deg, ${nextBadge.color} 0%, ${nextBadge.color}dd 100%);">
                                    ${progress.progress_percentage > 10 ? `<span class="text-xs font-bold text-white">${progress.progress_percentage}%</span>` : ''}
                                </div>
                            </div>
                        </div>

                        <!-- Amount Info -->
                        <div class="grid grid-cols-2 gap-4 text-sm">
                            <div class="bg-white rounded-lg p-3 border border-gray-200">
                                <p class="text-gray-500 text-xs mb-1">Current</p>
                                <p class="text-lg font-bold text-gray-900">$${parseFloat(progress.current_amount).toFixed(2)}</p>
                            </div>
                            <div class="bg-white rounded-lg p-3 border border-gray-200">
                                <p class="text-gray-500 text-xs mb-1">Needed</p>
                                <p class="text-lg font-bold" style="color: ${nextBadge.color};">$${parseFloat(progress.amount_needed).toFixed(2)}</p>
                            </div>
                        </div>

                        <div class="mt-4 text-center">
                            <p class="text-sm text-gray-600">
                                Spend a total of <span class="font-bold" style="color: ${nextBadge.color};">$${parseFloat(progress.next_threshold).toFixed(2)}</span> across all orders to earn this badge${voucherAmount > 0 ? ` and receive a <span class="font-bold text-green-600">$${voucherAmount.toFixed(2)} voucher</span>` : ''}!
                            </p>
                        </div>
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="text-center py-8">
                    <div class="badge-icon-large mx-auto mb-4" style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); box-shadow: 0 8px 20px #FFD70040;">
                        <i data-lucide="trophy" class="w-12 h-12 text-white"></i>
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 mb-2">Congratulations!</h3>
                    <p class="text-gray-600">You've earned all available badges!</p>
                </div>
            `;
        }

        content.innerHTML = html;
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
};

// Note: Initialization is handled in base.html's DOMContentLoaded event
// This ensures it runs after all scripts are loaded
