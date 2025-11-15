
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
    RADIUS: 50,
    CENTER_X: 60,
    CENTER_Y: 60,
    COLOR_ADJUSTMENT: 30
};

const INIT_DELAY = 300;

function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

function generateGradientColors(badgeColor) {
    if (!badgeColor) {
        return {
            start: '#f3f4f6',
            mid: '#e5e7eb',
            end: '#d1d5db'
        };
    }
    
    // Normalize color to uppercase for comparison
    const normalizedColor = badgeColor.toUpperCase();
    
    // Check if we have a preset gradient (check both original and normalized)
    if (GRADIENT_PRESETS[badgeColor]) {
        return GRADIENT_PRESETS[badgeColor];
    }
    if (GRADIENT_PRESETS[normalizedColor]) {
        return GRADIENT_PRESETS[normalizedColor];
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

function createGradient(badgeColor) {
    const colors = generateGradientColors(badgeColor);
    return `linear-gradient(135deg, ${colors.start} 0%, ${colors.mid} 50%, ${colors.end} 100%)`;
}

function applyWhiteIconStyles(icon) {
    if (!icon) return;
    
    // Apply white styling to match the left badge design
    icon.setAttribute('style', `
        color: #ffffff !important;
        fill: #ffffff !important;
        stroke: #ffffff !important;
        stroke-width: 2px !important;
    `);
    icon.classList.remove('text-gray-400', 'text-gray-500', 'text-gray-600');
    icon.classList.add('text-white');
    
    // Also style the SVG element if lucide has created it
    const svg = icon.querySelector('svg');
    if (svg) {
        svg.setAttribute('style', `
            color: #ffffff !important;
            fill: #ffffff !important;
            stroke: #ffffff !important;
            stroke-width: 2px !important;
        `);
        svg.style.color = '#ffffff';
        svg.style.fill = '#ffffff';
        svg.style.stroke = '#ffffff';
        svg.style.strokeWidth = '2px';
    }
}

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

    updateProgressBar(progress) {
        const badgeContainer = document.getElementById('badge-container');
        if (!badgeContainer) {
            return;
        }
        
        const progressRing = badgeContainer.querySelector('.progress-ring-fill');
        const progressBg = badgeContainer.querySelector('.progress-ring-bg');
        const indicator = badgeContainer.querySelector('.progress-indicator');
        
        if (!progressRing || !progressBg) {
            return;
        }

        const { next_badge: nextBadge, progress_percentage: progressPercent = 0 } = progress;
        
        const circumference = 2 * Math.PI * PROGRESS_RING.RADIUS;
        const offset = circumference - (progressPercent / 100 * circumference);
        
        progressRing.setAttribute('stroke-dashoffset', progress.circular_offset || offset);
        progressRing.setAttribute('stroke', 'url(#gradient-fill)');
        progressRing.setAttribute('stroke-width', '10');
        progressRing.style.opacity = '1';
        progressBg.style.opacity = '0.3';
        
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

    updateProfileBadge(progress) {
        const badgeContainer = document.getElementById('badge-container');
        if (!badgeContainer) {
            return;
        }
        
        if (badgeContainer.dataset.updating === 'true') {
            return;
        }
        badgeContainer.dataset.updating = 'true';
        
        try {
            const allProgressDivs = badgeContainer.querySelectorAll('.badge-with-circular-progress');
            if (allProgressDivs.length > 1) {
                for (let i = 1; i < allProgressDivs.length; i++) {
                    allProgressDivs[i].remove();
                }
            }
            
            const allCenterWrappers = badgeContainer.querySelectorAll('.badge-icon-large-center');
            if (allCenterWrappers.length > 1) {
                for (let i = 1; i < allCenterWrappers.length; i++) {
                    allCenterWrappers[i].remove();
                }
            }
            
            const allBadgeIcons = badgeContainer.querySelectorAll('.badge-icon-large-profile');
            if (allBadgeIcons.length > 1) {
                for (let i = 1; i < allBadgeIcons.length; i++) {
                    allBadgeIcons[i].remove();
                }
            }
            
            const allButtons = badgeContainer.querySelectorAll('button');
            if (allButtons.length > 1) {
                for (let i = 1; i < allButtons.length; i++) {
                    allButtons[i].remove();
                }
            }
            
        let badgeIcon = document.getElementById('badge-icon-profile');
            
        if (!badgeIcon) {
            badgeIcon = badgeContainer.querySelector('.badge-icon-large-profile');
        }
            
        if (!badgeIcon) {
                const centerWrapper = badgeContainer.querySelector('.badge-icon-large-center');
                if (centerWrapper) {
                    badgeIcon = centerWrapper.querySelector('.badge-icon-large-profile');
                }
        }
        
        const { current_badge: currentBadge, next_badge: nextBadge } = progress;

            if (!badgeIcon) {
                console.warn('Badge icon not found in badge-container.');
                return;
            }

        badgeContainer.style.opacity = '1';
        badgeContainer.style.display = 'block';
        badgeContainer.style.visibility = 'visible';

            badgeIcon.className = 'badge-icon-large-profile';
            badgeIcon.id = 'badge-icon-profile';
            
            const existingIcons = badgeIcon.querySelectorAll('i');
            existingIcons.forEach(icon => icon.remove());
            
            const existingSvgs = badgeIcon.querySelectorAll('svg');
            existingSvgs.forEach(svg => svg.remove());
            
        badgeIcon.innerHTML = '';
        
        const iconName = currentBadge ? (currentBadge.icon || 'award') : 'award';
        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', iconName);
        icon.className = 'w-12 h-12';
        badgeIcon.appendChild(icon);
        
        if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }

            if (currentBadge && currentBadge.color) {
                const badgeColor = currentBadge.color;
                const gradient = createGradient(badgeColor);
            
            badgeIcon.style.cssText = `
                background: ${gradient} !important;
                box-shadow: 0 8px 20px ${badgeColor}40 !important;
                width: 5rem !important;
                height: 5rem !important;
                border-radius: 50% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                flex-shrink: 0 !important;
                position: relative !important;
                z-index: 10 !important;
            `;
            
            // Apply white icon styles to match the left badge design - ensure icon is white
            applyWhiteIconStyles(icon);
            
            // Re-apply after a short delay to ensure lucide icons are rendered and styled white
            setTimeout(() => {
                applyWhiteIconStyles(icon);
                // Force white color on all SVG paths and elements
                const svg = icon.querySelector('svg');
                if (svg) {
                    svg.style.color = '#ffffff';
                    svg.style.fill = '#ffffff';
                    svg.style.stroke = '#ffffff';
                    const paths = svg.querySelectorAll('path, circle, line, polyline, polygon');
                    paths.forEach(path => {
                        path.style.stroke = '#ffffff';
                        path.style.fill = 'none';
                        path.setAttribute('stroke', '#ffffff');
                        path.setAttribute('fill', 'none');
                    });
                }
                if (typeof lucide !== 'undefined') {
                    lucide.createIcons();
                }
            }, 50);
            
            // One more pass after lucide fully renders
            setTimeout(() => {
                applyWhiteIconStyles(icon);
                const svg = icon.querySelector('svg');
                if (svg) {
                    svg.style.color = '#ffffff';
                    svg.style.fill = '#ffffff';
                    svg.style.stroke = '#ffffff';
                    const paths = svg.querySelectorAll('path, circle, line, polyline, polygon');
                    paths.forEach(path => {
                        path.style.stroke = '#ffffff';
                        path.style.fill = 'none';
                        path.setAttribute('stroke', '#ffffff');
                        path.setAttribute('fill', 'none');
                    });
                }
            }, 150);
        } else {
            badgeIcon.style.cssText = `
                background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 50%, #d1d5db 100%) !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1), 0 2px 6px rgba(0, 0, 0, 0.08) !important;
                width: 5rem !important;
                height: 5rem !important;
                border-radius: 50% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                flex-shrink: 0 !important;
                position: relative !important;
                z-index: 10 !important;
            `;
                
                icon.className = 'w-12 h-12 text-gray-500';
                applyGrayIconStyles(icon);
        }

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
            
            this.updateProgressBar(progress);
        } finally {
            badgeContainer.dataset.updating = 'false';
        }
    },

    updateModalContent(progress) {
        const { current_badge: currentBadge, next_badge: nextBadge } = progress;
        
        this.updateCurrentBadgeSection(currentBadge, progress);
        this.updateNextBadgeSection(nextBadge, progress);
        this.updateAllEarnedSection(currentBadge, nextBadge);
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    },

    updateCurrentBadgeSection(currentBadge, progress) {
        const section = document.getElementById('milestone-current-badge-section');
        if (!section) return;

        if (currentBadge && currentBadge.color) {
            const gradient = createGradient(currentBadge.color);
            const voucherAmount = currentBadge.voucher_amount || 0;
            const container = document.getElementById('milestone-current-badge-container');
            const icon = document.getElementById('milestone-current-badge-icon');
            const nameEl = document.getElementById('milestone-current-badge-name');
            const descEl = document.getElementById('milestone-current-badge-description');
            const voucherInfo = document.getElementById('milestone-current-voucher-info');
            const voucherAmountEl = document.getElementById('milestone-current-voucher-amount');
            const amountEl = document.getElementById('milestone-current-amount');

            if (container) {
                container.style.background = `linear-gradient(135deg, ${currentBadge.color}15 0%, ${currentBadge.color}05 100%)`;
                container.style.border = `2px solid ${currentBadge.color}`;
            }

            if (icon) {
                icon.style.background = gradient;
                icon.style.boxShadow = `0 8px 20px ${currentBadge.color}40`;
                const iconElement = icon.querySelector('i');
                if (iconElement) {
                    iconElement.setAttribute('data-lucide', currentBadge.icon || 'award');
                }
            }

            if (nameEl) {
                nameEl.textContent = currentBadge.name;
                nameEl.style.color = currentBadge.color;
            }

            if (descEl) {
                descEl.textContent = currentBadge.description || '';
            }

            if (voucherAmount > 0) {
                if (voucherInfo) voucherInfo.classList.remove('hidden');
                if (voucherAmountEl) {
                    voucherAmountEl.textContent = `Reward: $${voucherAmount.toFixed(2)} voucher received!`;
                }
            } else {
                if (voucherInfo) voucherInfo.classList.add('hidden');
            }

            if (amountEl) {
                amountEl.textContent = parseFloat(progress.current_amount).toFixed(2);
            }

            section.classList.remove('hidden');
        } else {
            section.classList.add('hidden');
        }
    },

    updateNextBadgeSection(nextBadge, progress) {
        const section = document.getElementById('milestone-next-badge-section');
        if (!section) return;

        if (nextBadge) {
            const voucherAmount = nextBadge.voucher_amount || 0;
            const gradient = createGradient(nextBadge.color);
            const icon = document.getElementById('milestone-next-badge-icon');
            const nameEl = document.getElementById('milestone-next-badge-name');
            const descEl = document.getElementById('milestone-next-badge-description');
            const voucherInfo = document.getElementById('milestone-next-voucher-info');
            const voucherAmountEl = document.getElementById('milestone-next-voucher-amount');
            const progressPercentEl = document.getElementById('milestone-progress-percentage');
            const progressBar = document.getElementById('milestone-progress-bar');
            const progressText = document.getElementById('milestone-progress-text');
            const currentSpendingEl = document.getElementById('milestone-current-spending');
            const amountNeededEl = document.getElementById('milestone-amount-needed');
            const thresholdTextEl = document.getElementById('milestone-next-threshold-text');

            if (icon) {
                icon.style.background = gradient;
                icon.style.boxShadow = `0 8px 20px ${nextBadge.color}40`;
                const iconElement = icon.querySelector('i');
                if (iconElement) {
                    iconElement.setAttribute('data-lucide', nextBadge.icon || 'award');
                }
            }

            if (nameEl) nameEl.textContent = nextBadge.name;
            if (descEl) descEl.textContent = nextBadge.description || '';

            if (voucherAmount > 0) {
                if (voucherInfo) voucherInfo.classList.remove('hidden');
                if (voucherAmountEl) {
                    voucherAmountEl.textContent = `Earn a $${voucherAmount.toFixed(2)} voucher when you reach this milestone!`;
                }
            } else {
                if (voucherInfo) voucherInfo.classList.add('hidden');
            }

            const progressPercent = progress.progress_percentage || 0;
            if (progressPercentEl) {
                progressPercentEl.textContent = `${progressPercent}%`;
            }

            if (progressBar) {
                progressBar.style.width = `${progressPercent}%`;
                progressBar.style.background = `linear-gradient(90deg, ${nextBadge.color} 0%, ${nextBadge.color}dd 100%)`;
            }

            if (progressText) {
                if (progressPercent > 10) {
                    progressText.textContent = `${progressPercent}%`;
                    progressText.classList.remove('hidden');
                } else {
                    progressText.classList.add('hidden');
                }
            }

            if (currentSpendingEl) {
                currentSpendingEl.textContent = `$${parseFloat(progress.current_amount).toFixed(2)}`;
            }

            if (amountNeededEl) {
                amountNeededEl.textContent = `$${parseFloat(progress.amount_needed).toFixed(2)}`;
                amountNeededEl.style.color = nextBadge.color;
            }

            if (thresholdTextEl) {
                const thresholdText = `Spend a total of $${parseFloat(progress.next_threshold).toFixed(2)} across all orders to earn this badge`;
                const voucherText = voucherAmount > 0 ? ` and receive a $${voucherAmount.toFixed(2)} voucher` : '';
                thresholdTextEl.innerHTML = `<span class="text-sm text-gray-600">${thresholdText}${voucherText}!</span>`;
            }

            section.classList.remove('hidden');
        } else {
            section.classList.add('hidden');
        }
    },

    updateAllEarnedSection(currentBadge, nextBadge) {
        const section = document.getElementById('milestone-all-earned-section');
        if (!section) return;
        
        if (currentBadge && !nextBadge) {
            section.classList.remove('hidden');
        } else {
            section.classList.add('hidden');
        }
    }
};
