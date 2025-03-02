
# $Id: scour.in,v 1.1.16.6.2.7 2009/07/16 19:27:13 steve Exp $
# Deletes old data files.
#
# Recursively deletes files older than a specified number of days from a
# specified set of directories.  The directories, retention time in days,
# and an optional shell filename pattern appear, separated by tab characters
# one directory per line, in a configuration file named on the command line.
#
# If no files have been written under a directory since the last time scour was
# run, it will skip deleting old files and log an error message instead.
#
# WARNING: scour follows symbolic links, so don't put symbolic links to
# directories you don't want scoured under data directories.

PATH=/home/steve/Projects/ldm/bin:/bin:/usr/bin
CONFFILE=`regutil /scour/config-path`  # default, if no args
VERBOSEFLAG=
DEBUGFLAG=
ERRS=
PROG=`basename $0`
LOGGER="echo $PROG: "
TZ=UTC0 export TZ
LOG_LDM=local0

while [ "$1" != "" ]
do
	case "$1" in
	-v)
		VERBOSEFLAG=1
		;;
	-x)
		DEBUGFLAG=1
		;;
	-l)						# logs to syslogd
		LOGGER="logger -t $PROG -p $LOG_LDM.notice"
		;;
	-*)
		$LOGGER "unrecognized flag ($1)"
		ERRS=1
		;;
	*)
		if [ $# -ne 1 ]
		then
			$LOGGER "only 1 conf file argument permitted"
			ERRS=1
		fi
		CONFFILE=$1
		;;
	esac
	shift
done

if [ "$ERRS" != "" ]
then
	$LOGGER "usage: $PROG [-l] [-v] [-x] [config-file]"
	exit 1
fi

if [ "$VERBOSEFLAG" != "" ]
then
	$LOGGER "Starting Up"
fi

# Different find(1) utilities have different meanings for the "-mtime" argument.
# Discover the meaning for the find(1) utility that will be used.
#
dayOffsetName=scour_$$
trap 'rm -f /tmp/$dayOffsetName' EXIT
if touch /tmp/$dayOffsetName; then
    sleep 2
    #
    # NOTE: OSF/1's find(1) utility doesn't conform to the Standard
    # because the CWD must be changed in order to get this test to work.
    #
    dir=`pwd`
    cd /tmp
    if find $dayOffsetName -mtime 0 |
	    grep $dayOffsetName >/dev/null; then
	DAY_OFFSET=1
    elif find $dayOffsetName -mtime 1 |
	    grep $dayOffsetName >/dev/null; then
	DAY_OFFSET=0
    else
	$LOGGER "Couldn't discover meaning of '-mtime' argument of find(1)"
	exit 1
    fi
    cd $dir
    rm /tmp/$dayOffsetName
else
    $LOGGER "Couldn't create '-mtime' discovery-file /tmp/$dayOffsetName"
    exit 1
fi

while read dir age pattern; do
    if [ x$dir = x ]	# ignore blank lines
    then
        continue
    fi

    case $dir in
      \#*) 		# ignore comments
	continue
	;;
      *)
	if [ x$pattern = x ]
	then
		pattern="*"
	fi

        # Convert directory specification to absolute pathname: follow symbolic
        # links (because find(1) doesn't) and perform tilde-expansion.
	#
	# NB: The statement 
	#     edir=`csh -f -c "cd $dir && /bin/pwd"`
        # causes the read(1) of the enclosing while-loop to return EOF if the
        # directory doesn't exist.
	#
	if edir=`cd "$dir" && /bin/pwd`; then
	    : true
	else
	    $LOGGER "directory $dir does not exist, skipping"
	    continue
	fi

	if [ "$DEBUGFLAG" != "" ]
	then
	    echo "dir=$dir age=$age pattern=$pattern edir=$edir"
	fi

	(
	    if cd $edir
	    then
		# if either "$edir/.scour$pattern" doesn't exist yet OR
		#           there are files newer than "$edir/.scour$pattern"
		# then
		#     delete old files and create "$edir/.scour$pattern"
		# else
		#     skip deletions and log message
		if  [ ! -f ".scour$pattern" ] || \
		    [ -n "`find . -newer \".scour$pattern\" 2>/dev/null | \
			head -1`" ]
		then
		    FINDAGE=`echo $age $DAY_OFFSET - p|dc`
		    if [ "$VERBOSEFLAG" != "" ]
		    then
			BEFORE=`du -s . 2>/dev/null | \
			    sed 's/^ *\([0-9]*\).*/\1/'`
		    fi
		    find . -type f -mtime +$FINDAGE -name "$pattern" -print \
                        | sed 's/\([^\n]\)/\\\1/g' \
                        | xargs rm -f && touch ".scour$pattern"
		    if [ "$VERBOSEFLAG" != "" ]
		    then
			AFTER=`du -s . 2>/dev/null | \
			    sed 's/^ *\([0-9]*\).*/\1/'`
			# set DELETED to max(0, BEFORE - AFTER)
			DELETED=`echo $BEFORE $AFTER|\
			awk '{diff=$1-$2; print (diff < 0) ? 0 : diff;}'`
			$LOGGER "$DELETED blocks from $edir/$pattern (>" \
			    "$age days old)"
		    fi
		else
		    $LOGGER "skipping, no recent files in $edir/$pattern"
		fi
	    fi
	)
	;;
    esac
done < $CONFFILE

if [ "$VERBOSEFLAG" != "" ]
then
	$LOGGER exiting ...
fi
