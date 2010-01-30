# Copyright (C) 2009,2010 Anil Madhavapeddy <anil@recoil.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Parse and sync Adium logs with a LifeDB

import os, sys
sys.path.append("../../support")
from pkg_resources import require
require("simplejson")
require("lxml")
from xml.dom.minidom import parse
from datetime import datetime
import dateutil.parser
import time
import hashlib
import base64
import xml
import lxml.html,simplejson
import Perscon_utils

def parseLog(chatlog):
    try:
        tree = parse(chatlog)
    except xml.parsers.expat.ExpatError, err:
        print >> sys.stderr, "Warning: %s is not XML, skipping" % chatlog
        return
    chats = tree.getElementsByTagName('chat')
    for chat in chats:
        account = chat.getAttribute('account')
        service = chat.getAttribute('service').lower()
        if service == "gtalk":
           service = "jabber"
        version = chat.getAttribute('version')
        transport = chat.getAttribute('transport')
        uri = chat.namespaceURI
        info = { 'account': account, 'service': service, 'uri': uri }
        if version != "": info['version'] = version
        if transport != "": info['transport'] = transport
        msgs = chat.getElementsByTagName('message')
        # need to accumulate the list of participants in the chat based on who
        # talks that isnt the sender
        participants = []
        for msg in msgs:
            sender = msg.getAttribute('sender')
            if sender != account and sender not in participants:
               participants.append(sender)
        for msg in msgs:
            sender = msg.getAttribute('sender')
            tm = msg.getAttribute('time')
            time_parsed = dateutil.parser.parse(tm)
            tt = time_parsed.timetuple()
            time_float = time.mktime(tt)
            # very dodgily ignoring unicode errors here, but copes with some malformed messages
            body = unicode.join(u'',map(lambda x: unicode(x.toxml(encoding='utf-8'), errors='ignore'), msg.childNodes))
            body = lxml.html.fromstring(body).text_content()
            m = { 'origin':'com.adium' }
            m['mtime'] = time_float
            # this message originated from the current user, so its from us
            # and to the participants
            m['frm'] = [{ 'ty' : service, 'id': sender }]
            if sender == account:
                m['to'] = map(lambda x: { 'ty': service, 'id' : x }, participants)
            else:
                m['to'] = [{ 'ty' :service, 'id': account }]
            meta={}
            meta.update(info)
            m['meta'] = meta 
            h = hashlib.sha1()
            h.update(service)
            h.update(account)
            h.update(sender)
            h.update(tm)
            h.update(body)
            uid = h.hexdigest()
            m['uid'] = uid
            mj = simplejson.dumps(m,indent=2)
            Perscon_utils.rpc('thing/' + uid, data=mj)

def main():
    logdir = "%s/Library/Application Support/Adium 2.0/Users/Default/Logs/" % os.getenv("HOME")
    if not os.path.isdir(logdir):
        print >> sys.stderr, "Unable to find Adium log dir in: %s" % logdir
        sys.exit(1)
    uri = "http://localhost:5985/"
    Perscon_utils.init_url (uri)
    for root, dirs, files in os.walk(logdir):
        for f in files:
            logfile = os.path.join(root, f)
            parseLog(logfile)
    
if __name__ == "__main__":
    main()
