async function startCapture() {
    const settings = getSettings();
    isRunning = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    
    try {
      const response = await fetch('http://localhost:5000/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: settings.url,
          selector: settings.selector,
          email: settings.email,
          duration: settings.duration,
          scheduled: scheduleToggle.checked,
          interval: settings.interval
        })
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        logMessage('Capture started successfully');
        updateStatus('Capture in progress...');
        
        if (scheduleToggle.checked) {
          startBtn.textContent = 'Running on Schedule';
        } else {
          startBtn.textContent = 'Capture in Progress';
        }
      } else {
        logMessage(`Error: ${data.message}`);
        updateStatus(`Error: ${data.message}`, true);
        stopCapture(false);
      }
    } catch (error) {
      logMessage(`Connection error: ${error.message}`);
      updateStatus('Failed to connect to the backend', true);
      stopCapture(false);
    }
  }
  
  async function stopCapture(userInitiated = true) {
    try {
      const response = await fetch('http://localhost:5000/stop', {
        method: 'POST'
      });
      
      const data = await response.json();
      logMessage(data.message);
    } catch (error) {
      logMessage(`Connection error during stop: ${error.message}`);
    }
    
    isRunning = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    startBtn.textContent = 'Start Single Capture';
    
    if (userInitiated) {
      updateStatus('Capture stopped by user');
    } else {
      updateStatus('Ready to start');
    }
  }