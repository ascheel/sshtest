package main

import (
	"os"
	"log"
	"golang.org/x/crypto/ssh"
	//"golang.org/x/crypto/ssh/knownhosts"
	"path/filepath"
	"bufio"
	"io"
	"fmt"
	//"strconv"
	"net"
	"errors"
	"syscall"
	"time"
	//"strings"
	"reflect"
)

type SSH struct {
	host     string
	user     string
	port     string
	key      string
	password string
	errCode  uint8
	errText  string
	errRaw   error
}

func check(e error) {
	if e != nil {
		log.Fatal(e)
	}
}

func readSize(file *os.File) int64 {
	stat, err := file.Stat()
	check(err)
	return stat.Size()
}

func readFile(filename string) []byte {
	file, err := os.Open(filename)
	check(err)
	defer file.Close()
	// Read the file into a byte slice
	bs := make([]byte, readSize(file))
	_, err = bufio.NewReader(file).Read(bs)
	if err != nil && err != io.EOF {
		fmt.Println(err)
	}
	return bs
}

func sshConnectWithPKey(connInfo *SSH) (*ssh.Client, *ssh.Session, error) {
	hostString := net.JoinHostPort(connInfo.host, connInfo.port)
	pKey := readFile(connInfo.key)
	signer, err := ssh.ParsePrivateKey(pKey)
	check(err)

	//hostKeyCallback, err := knownhosts.New(knownHostsFile)
	//check(err)

	timeout, _ := time.ParseDuration("5s")

	conf := &ssh.ClientConfig{
		User: connInfo.user,
		Auth: []ssh.AuthMethod{
			ssh.PublicKeys(signer),
		},
		Timeout: timeout,
	}

	conf.HostKeyCallback = ssh.InsecureIgnoreHostKey()

	client, err := ssh.Dial("tcp", hostString, conf)
	if err != nil {
		return nil, nil, err
	}

	session, err := client.NewSession()
	if err != nil {
		fmt.Println("Failure with client.NewSession()")
		return nil, nil, err
	}

	return client, session, nil
}

func tryConnectWithPrivateKey(connInfo *SSH) bool {
	if len(connInfo.port) == 0 {
		connInfo.port = "22"
	}

	client, session, err := sshConnectWithPKey(connInfo)
	if err != nil {
		//connInfo.errRaw = err
		return false
	}
	command := "ls -l /"
	_, err = session.CombinedOutput(command)
	if err != nil {
		//connInfo.errRaw = err
		return false
	}
	if client == nil || session == nil {
		log.Fatal("You shouldn't get here.")
		return false
	}
	connInfo.errCode = 0
	connInfo.errText = "success"
	return true
}

func sshCheck(err error) {
	if err != nil {
		if errors.Is(err, syscall.ECONNREFUSED) {
			fmt.Println("Connection refused.  CAUGHT IT.")
		}
	}
}

func tryConnect(connInfo *SSH) {
	if len(connInfo.key) == 0 && len(connInfo.password) == 0 {
		log.Fatalln("No key or password provided.")
	} else if len(connInfo.key) > 0 && len(connInfo.password) > 0 {
		log.Fatalln("Application does not yet support passwords AND keys both.")
	} else if len(connInfo.host) == 0 {
		log.Fatalln("No host provided.")
	} else if len(connInfo.port) == 0 {
		connInfo.port = "22"
	}
	if len(connInfo.key) > 0 {
		// Connect with key
		tryConnectWithPrivateKey(connInfo)
	} else if len(connInfo.password) > 0 {
		// Connect with password
		//return tryConnectWithPassword(connInfo)
	}
}

func printStruct(connInfo *SSH) {
	s := reflect.ValueOf(&connInfo).Elem().Elem()
	typeOfSSH := s.Type()
	fmt.Println(typeOfSSH)
	for i := 0; i < s.NumField(); i++ {
	 	f := s.Field(i)
		fmt.Println(f)
		fmt.Printf("%d: %s %s = %v\n", i, typeOfSSH.Field(i).Name, f.Type(), f.Interface())
	}
}

func handleExit(connInfo *SSH) {
	printStruct(connInfo)
	fmt.Printf("%+v\n", connInfo)
}

func main() {
	homedir, err := os.UserHomeDir()
	check(err)

	sshdir := filepath.Join(homedir, ".ssh")
	pKeyPath := filepath.Join(sshdir, "id_rsa_legion")

	connInfo := SSH {
		host: "192.168.1.15",
		user: "art",
		port: "22",
		key: pKeyPath,
		password: "",
	}

	tryConnect(&connInfo)
	handleExit(connInfo)

	// if success {
	// 	fmt.Println("Successful.")
	// } else {
	// 	fmt.Println("Failure.")
	// 	var errCode uint8 = 0
	// 	var errText string
	// 	var e *net.OpError
	// 	// dial tcp 192.168.1.198:22: connect: connection refused
	// 	// ssh: handshake failed: ssh: unable to authenticate, attempted methods [none publickey], no supported methods remain
	// 	// dial tcp 192.168.1.3:22: connect: no route to host
	// 	// dial tcp 172.217.14.78:22: i/o timeout

	// 	if errors.As(err, &e) {
	// 		errText = e.Err.Error()
	// 		if errText == "i/o timeout" {
	// 			errCode = 1
	// 		} else if errText == "connection refused" {
	// 			errCode = 2
	// 		} else if errText == "no route to host" {
	// 			errCode = 3
	// 		}
	// 		fmt.Println(errText)
	// 		fmt.Println(errCode)
	// 	}
	// 	//subs := strings.SplitN(err.Error(), ":", 1)
	// 	fmt.Println("Failure with ssh.Dial()")
	// 	fmt.Println(err)
	// }
}

