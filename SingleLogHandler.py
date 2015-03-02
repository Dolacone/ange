import logging

class SingleLogHandler(logging.Handler):
  def __init__(self, logFile):
    logging.Handler.__init__(self)
    self.logFile = '%s' % (logFile)
  def emit(self, record):
    fileDropper = open(self.logFile, 'w')
    fileDropper.write(self.format(record))
    fileDropper.close()
