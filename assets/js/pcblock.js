function isMobileDevice() {
            var userAgent = navigator.userAgent || navigator.vendor || window.opera;

            if (/android/i.test(userAgent)) {
                return "Android";
            }
            if (/iPhone/i.test(userAgent)) {
                return "iPhone";
            }
            return false;
        }

        var device = isMobileDevice();

        if (device) {

        } else {

            window.location.href = "about:blank"; // Impede o acesso em outros dispositivos
        }