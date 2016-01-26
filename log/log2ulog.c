/**
 * Copyright 2015 University Corporation for Atmospheric Research. All rights
 * reserved. See the the file COPYRIGHT in the top-level source-directory for
 * licensing conditions.
 *
 *   @file: log2ulog.c
 * @author: Steven R. Emmerson
 *
 * This file provides the `log.h` API using `ulog.c`.
 */

#include "config.h"

#include "mutex.h"
#include "log.h"
#include "ulog.h"

#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef _XOPEN_PATH_MAX
    #define _XOPEN_PATH_MAX 1024
#endif

/******************************************************************************
 * Private API:
 ******************************************************************************/

/**
 * The mapping from `log` logging levels to `ulog` priorities:
 */
int                  log_syslog_priorities[] = {
        LOG_DEBUG, LOG_INFO, LOG_NOTICE, LOG_WARNING, LOG_ERR
};

/**
 *  Logging level. The initial value must be consonant with the initial value of
 *  `logMask` in `ulog.c`.
 */
static log_level_t loggingLevel = LOG_LEVEL_DEBUG;

/******************************************************************************
 * Package-private API:
 ******************************************************************************/

/**
 * Returns the default destination for log messages. If the current process is a
 * daemon, then the default destination will be the system logging daemon;
 * otherwise, the default destination will be to the standard error stream.
 *
 * @retval ""   Log to the system logging daemon
 * @retval "-"  Log to the standard error stream
 */
const char* log_get_default_destination(void)
{
    return log_am_daemon() ? "" : "-";
}

/**
 * Emits a single log message.
 *
 * @param[in] level  Logging level.
 * @param[in] msg    The message.
 */
void log_write_one(
        const log_level_t    level,
        const Message* const   msg)
{
    (void)ulog(log_get_priority(level), "%s:%s():%d %s", msg->loc.file,
            msg->loc.func, msg->loc.line, msg->string);
}

/**
 * Emits an error message. Used internally when an error occurs in this logging
 * module.
 *
 * @param[in] fmt  Format of the message.
 * @param[in] ...  Format arguments.
 */
void log_internal(
        const char* const fmt,
                          ...)
{
    va_list args;
    va_start(args, fmt);
    (void)vulog(log_get_priority(LOG_LEVEL_ERROR), fmt, args);
    va_end(args);
}

/**
 * Initializes the logging module. Should be called before any other function.
 * - `log_get_destination()` will return ""
 *   - ""  if the process is a daemon
 *   - "-" otherwise
 * - `log_get_facility()` will return `LOG_LDM`.
 * - `log_get_level()` will return `LOG_LEVEL_NOTICE`.
 *
 * @param[in] id       The pathname of the program (e.g., `argv[0]`). Caller may
 *                     free.
 * @retval    0        Success.
 * @retval    -1       Error. Logging module is in an unspecified state.
 */
int log_impl_init(
        const char* id)
{
    const char* dest = log_get_default_destination();
    char progname[_XOPEN_PATH_MAX];
    strncpy(progname, id, sizeof(progname))[sizeof(progname)-1] = 0;
    id = basename(progname);
    int status = openulog(id, LOG_PID, LOG_LDM, dest);
    if (status != -1)
        status = log_set_level(LOG_LEVEL_NOTICE);
    return status ? -1 : 0;
}

/**
 * Finalizes the logging module.
 *
 * @retval 0   Success.
 * @retval -1  Failure. Logging module is in an unspecified state.
 */
int log_impl_fini(void)
{
    log_lock();
    int status = closeulog();
    log_unlock();
    return status ? -1 : 0;
}

/******************************************************************************
 * Public API:
 ******************************************************************************/

/**
 * Enables logging down to a given level.
 *
 * @param[in] level  The lowest level through which logging should occur.
 * @retval    0      Success.
 * @retval    -1     Failure.
 */
int log_set_level(
        const log_level_t level)
{
    int status;
    if (!log_vet_level(level)) {
        status = -1;
    }
    else {
        static int ulogUpTos[LOG_LEVEL_COUNT] = {LOG_UPTO(LOG_DEBUG),
                LOG_UPTO(LOG_INFO), LOG_UPTO(LOG_NOTICE), LOG_UPTO(LOG_WARNING),
                LOG_UPTO(LOG_ERR)};
        log_lock();
        (void)setulogmask(ulogUpTos[level]);
        loggingLevel = level;
        log_unlock();
        status = 0;
    }
    return status;
}

/**
 * Returns the current logging level.
 *
 * @return The lowest level through which logging will occur. The initial value
 *         is `LOG_LEVEL_DEBUG`.
 */
log_level_t log_get_level(void)
{
    log_lock();
    log_level_t level = loggingLevel;
    log_unlock();
    return level;
}

/**
 * Sets the facility that will be used (e.g., `LOG_LOCAL0`) when logging to the
 * system logging daemon. Should be called after `log_impl_init()`.
 *
 * @param[in] facility  The facility that will be used when logging to the
 *                      system logging daemon.
 */
int log_set_facility(
        const int facility)
{
    log_lock();
    const char* const id = log_get_id();
    const unsigned    options = log_get_options();
    const char* const output = log_get_destination();
    int               status = openulog(id, options, facility, output);
    log_unlock();
    return status == -1 ? -1 : 0;
}

/**
 * Returns the facility that will be used when logging to the system logging
 * daemon (e.g., `LOG_LOCAL0`).
 *
 * @return The facility that will be used when logging to the system logging
 *         daemon (e.g., `LOG_LOCAL0`).
 */
int log_get_facility(void)
{
    log_lock();
    int facility = getulogfacility();
    log_unlock();
    return facility;
}

/**
 * Sets the logging identifier. Should be called between `log_impl_init()` and
 * `log_impl_fini()`.
 *
 * @param[in] id        The new identifier. Caller may free.
 * @retval    0         Success.
 * @retval    -1        Failure.
 */
int log_set_id(
        const char* const id)
{
    int status;
    if (id == NULL) {
        status = -1;
    }
    else {
        log_lock();
        setulogident(id);
        log_unlock();
        status = 0;
    }
    return status;
}

/**
 * Returns the logging identifier.
 *
 * @return The logging identifier. The initial value is "ulog".
 */
const char* log_get_id(void)
{
    log_lock();
    const char* const id = getulogident();
    log_unlock();
    return id;
}

/**
 * Sets the logging options.
 *
 * @param[in] options  The logging options. Bitwise or of
 *                         LOG_NOTIME      Don't add timestamp
 *                         LOG_PID         Add process-identifier.
 *                         LOG_IDENT       Add logging identifier.
 *                         LOG_MICROSEC    Use microsecond resolution.
 *                         LOG_ISO_8601    Use timestamp format
 *                             <YYYY><MM><DD>T<hh><mm><ss>[.<uuuuuu>]<zone>
 */
void log_set_options(
        const unsigned options)
{
    log_lock();
    ulog_set_options(~0u, options);
    log_unlock();
}

/**
 * Returns the logging options.
 *
 * @return The logging options. Bitwise or of
 *             LOG_NOTIME      Don't add timestamp
 *             LOG_PID         Add process-identifier.
 *             LOG_IDENT       Add logging identifier.
 *             LOG_MICROSEC    Use microsecond resolution.
 *             LOG_ISO_8601    Use timestamp format
 *                             <YYYY><MM><DD>T<hh><mm><ss>[.<uuuuuu>]<zone>
 *         The initial value is `0`.
 */
unsigned log_get_options(void)
{
    log_lock();
    const unsigned opts = ulog_get_options();
    log_unlock();
    return opts;
}

/**
 * Sets the logging destination. Should be called between log_init() and
 * log_fini().
 *
 * @param[in] dest     The logging destination. Caller may free. One of <dl>
 *                         <dt>""   <dd>The system logging daemon.
 *                         <dt>"-"  <dd>The standard error stream.
 *                         <dt>else <dd>The file whose pathname is `dest`.
 *                     </dl>
 * @retval    0        Success.
 * @retval    -1       Failure.
 */
int log_set_destination(
        const char* const dest)
{
    log_lock();
    const char* const id = getulogident();
    const unsigned    options = ulog_get_options();
    int               status = openulog(id, options, LOG_LDM, dest);
    log_unlock();
    return status == -1 ? -1 : 0;
}

/**
 * Returns the logging destination. Should be called between log_init() and
 * log_fini().
 *
 * @return       The logging destination. One of <dl>
 *                   <dt>""      <dd>The system logging daemon.
 *                   <dt>"-"     <dd>The standard error stream.
 *                   <dt>else    <dd>The pathname of the log file.
 *               </dl>
 */
const char* log_get_destination(void)
{
    log_lock();
    const char* path = getulogpath();
    log_unlock();
    return path == NULL ? "" : path;
}