// Enhanced polyfill for Underscore.js compatibility issues
// Fixes _.contains and other deprecated methods

(function() {
    'use strict';
    
    // Enhanced polyfill function
    function addEnhancedPolyfills(obj, scope) {
        if (!obj || typeof obj !== 'object') return false;
        
        var added = false;
        
        // Fix _.contains -> _.includes
        if (!obj.contains && obj.includes) {
            obj.contains = obj.includes;
            added = true;
        }
        
        // Add missing methods that might cause errors
        if (!obj.off && obj.unbind) {
            obj.off = obj.unbind;
            added = true;
        }
        
        if (!obj.on && obj.bind) {
            obj.on = obj.bind;
            added = true;
        }
        
        // Ensure basic event methods exist
        if (!obj.off && !obj.unbind) {
            obj.off = function() { return this; };
            added = true;
        }
        
        if (!obj.on && !obj.bind) {
            obj.on = function() { return this; };
            added = true;
        }
        
        if (added) {
            console.log('Twitter API Service: Enhanced polyfills added for', scope);
        }
        
        return added;
    }
    
    // Apply polyfills to global objects
    function applyGlobalPolyfills() {
        var applied = false;
        
        if (typeof _ !== 'undefined') {
            applied = addEnhancedPolyfills(_, 'global _') || applied;
        }
        
        if (typeof window !== 'undefined' && window._) {
            applied = addEnhancedPolyfills(window._, 'window._') || applied;
        }
        
        // Also check jQuery if present
        if (typeof $ !== 'undefined') {
            if (!$.fn.off) {
                $.fn.off = $.fn.unbind || function() { return this; };
                applied = true;
            }
            if (!$.fn.on) {
                $.fn.on = $.fn.bind || function() { return this; };
                applied = true;
            }
        }
        
        return applied;
    }
    
    // Apply immediately
    applyGlobalPolyfills();
    
    // Monitor for library loading
    var checkCount = 0;
    var maxChecks = 100;
    
    function checkAndApplyPolyfills() {
        checkCount++;
        
        if (applyGlobalPolyfills()) {
            // Continue checking for new libraries
        }
        
        if (checkCount < maxChecks) {
            setTimeout(checkAndApplyPolyfills, 50);
        }
    }
    
    // Start monitoring
    setTimeout(checkAndApplyPolyfills, 1);
    
    // Apply when DOM is ready
    if (typeof document !== 'undefined') {
        function onReady() {
            setTimeout(function() {
                applyGlobalPolyfills();
                checkAndApplyPolyfills();
            }, 1);
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', onReady);
        } else {
            onReady();
        }
    }
    
    // Handle window load event
    if (typeof window !== 'undefined') {
        window.addEventListener('load', function() {
            setTimeout(applyGlobalPolyfills, 1);
        });
    }
    
})();